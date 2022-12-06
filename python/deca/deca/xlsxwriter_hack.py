from xlsxwriter import Workbook
from xlsxwriter.exceptions import InvalidWorksheetName, DuplicateWorksheetName
import re


class DecaWorkBook(Workbook):
    def __init__(self, *kargs, **kwargs):
        Workbook.__init__(self, *kargs, **kwargs)

    '''
    Code was taken from the xlsxwriter package and modified to handle longer names. That code is covered by this license
    
    Copyright (c) 2013, John McNamara <jmcnamara@cpan.org>
    All rights reserved.
    
    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:
    
    1. Redistributions of source code must retain the above copyright notice, this
       list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright notice,
       this list of conditions and the following disclaimer in the documentation
       and/or other materials provided with the distribution.
    
    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
    ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
    ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    
    The views and conclusions contained in the software and documentation are those
    of the authors and should not be interpreted as representing official policies,
    either expressed or implied, of the FreeBSD Project.

    '''
    def _check_sheetname(self, sheetname, is_chartsheet=False):
        # Check for valid worksheet names. We check the length, if it contains
        # any invalid chars and if the sheetname is unique in the workbook.
        invalid_char = re.compile(r'[\[\]:*?/\\]')

        # Increment the Sheet/Chart number used for default sheet names below.
        if is_chartsheet:
            self.chartname_count += 1
        else:
            self.sheetname_count += 1

        # Supply default Sheet/Chart sheetname if none has been defined.
        if sheetname is None or sheetname == '':
            if is_chartsheet:
                sheetname = self.chart_name + str(self.chartname_count)
            else:
                sheetname = self.sheet_name + str(self.sheetname_count)

        # Check that sheet sheetname is <= 255. Excel file limit.
        if len(sheetname) > 255:
            raise InvalidWorksheetName(
                "Excel worksheet name '%s' must be <= 255 chars." %
                sheetname)

        # Check that sheetname doesn't contain any invalid characters
        if invalid_char.search(sheetname):
            raise InvalidWorksheetName(
                "Invalid Excel character '[]:*?/\\' in sheetname '%s'." %
                sheetname)

        # Check that the worksheet name doesn't already exist since this is a
        # fatal Excel error. The check must be case insensitive like Excel.
        for worksheet in self.worksheets():
            if sheetname.lower() == worksheet.name.lower():
                raise DuplicateWorksheetName(
                    "Sheetname '%s', with case ignored, is already in use." %
                    sheetname)

        return sheetname
