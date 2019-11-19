# -*- coding: utf-8 -*-
# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Task for executing volatility."""

from __future__ import unicode_literals

import os

from turbinia import config
from turbinia.evidence import VolatilityReport
from turbinia.workers import TurbiniaTask

MAX_REPORT_SIZE = 2**30  # 1 GiB


class VolatilityTask(TurbiniaTask):
  """Task to execute volatility.

  Attributes:
    module(str): The name of the volatility module to run.
  """

  def __init__(self, module='test', *args, **kwargs):
    super(VolatilityTask, self).__init__(*args, **kwargs)
    self.module = module

  def run(self, evidence, result):
    """Run volatility against evidence.

    Args:
        evidence (Evidence object):  The evidence we will process.
        result (TurbiniaTaskResult): The object to place task results into.

    Returns:
        TurbiniaTaskResult object.
    """
    config.LoadConfig()

    # Create a path that we can write the new file to.
    output_file_path = os.path.join(
        self.output_dir, '{0:s}.txt'.format(self.id))
    # Create the new Evidence object that will be generated by this Task.
    output_evidence = VolatilityReport(source_path=output_file_path)

    # TODO: Add in config options for Turbinia
    cmd = (
        'vol.py -f {0:s} --profile={1:s} {2:s} --output=text '
        '--output-file={3:s}').format(
            evidence.local_path, evidence.profile, self.module,
            output_file_path).split()

    result.log('Running volatility as [{0:s}]'.format(' '.join(cmd)))
    res = self.execute(cmd, result, new_evidence=[output_evidence], close=True)

    if res == 0:
      success = True
      # Get report data from the output file.
      try:
        file_size = os.stat(output_file_path).st_size
      except (IOError, OSError) as exception:
        msg = 'Unable to determine size of output file {0:s}: {1!s}'.format(
            output_file_path, exception)
        summary = 'Volatility ran successfully, but no output file was created'
        result.log(msg)
        result.close(self, success=False, status=summary)
        return result

      if file_size > MAX_REPORT_SIZE:
        result.log(
            'Volatility report output size ({0:d}) is greater than max report '
            'size ({1:d}). Truncating report to max size'.format(
                file_size, MAX_REPORT_SIZE))
        summary = (
            'Volatility module {0:s} successfuly ran (report truncated)'.format(
                self.module))
      else:
        summary = 'Volatility module {0:s} successfully ran'.format(self.module)

      with open(output_file_path, 'rb') as fh:
        report_data = fh.read(MAX_REPORT_SIZE)
        try:
          output_evidence.text_data = report_data.decode('utf-8')
        except UnicodeDecodeError as e:
          success = False
          summary = 'Volatility report could not be read: {0!s}'.format(e)

      result.report_data = output_evidence.text_data
      result.close(self, success=success, status=summary)
    else:
      summary = 'Volatility module {0:s} failed to run'.format(self.module)
      result.close(self, success=False, status=summary)

    return result
