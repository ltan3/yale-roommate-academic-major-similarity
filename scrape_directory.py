import sys
import re
import time
import random
import requests
from html.parser import HTMLParser
from csv import DictWriter

def wait_random():
  time.sleep(random.uniform(0.5, 2))


class FBStudentModel():
  student_attrs = ['first_name',
                   'last_name',
                   'grad_year',
                   'college',
                   'email',
                   'img',
                   'other',
                   'room',
                   'birthday',
                   'major',
                   'city',
                   'state',
                   'zip']

  def __init__(self, f_out):
    print('FBStudentModel initalized')
    self.csv_writer = DictWriter(f_out, self.student_attrs, restval='')
    self.csv_writer.writeheader()
    self.new_student()

  def new_student(self):
    self.curr_student = {}

  def add_attr(self, attr, value):
    assert(attr in self.student_attrs)

    if attr == 'other':
      self.add_other(value)
    else:
      self.curr_student[attr] = value.strip()

  def add_other(self, value):
    if 'other' not in self.curr_student:
      self.curr_student['other'] = ''

    self.curr_student['other'] += value.strip() + '\t'


  def write_student(self):

    if len(self.curr_student) != 0:

      if 'other' in self.curr_student:
        # Parse room number
        lines = self.curr_student['other'].split('\t')
        match = re.search(r'[\w]+-[\w\d]+', lines[0])
        if match:
            r = match.group(0)
            if r[-1].isalpha():
                r = r[:-1]
            self.curr_student['room'] = r

        # Parse birthday and major
        lines = self.curr_student['other'].strip().split('\t')
        if len(lines) >= 2:
            match = re.search(r'[\w]{3} [\d]{1,2}', lines[-1])
            if match:
                self.curr_student['birthday'] = match.group(0)
                self.curr_student['major'] = lines[-2]
            else:
                self.curr_student['major'] = lines[-1]

        # Parse city, state, zip
        text = self.curr_student['other'].strip()
        if text:
            match = re.search(r'([ \w]+), ([A-Z]{2}) (\d{5})', text)
            if match:
                self.curr_student['city'] = match.group(1)
                self.curr_student['state'] = match.group(2)
                self.curr_student['zip'] = match.group(3)
            else:
              match = re.search(r'([ \w]+), ([A-Z]{2})', text)
              if match:
                self.curr_student['city'] = match.group(1)
                self.curr_student['state'] = match.group(2)

      # print('Writing student')
      # print(self.curr_student)
      self.csv_writer.writerow(self.curr_student)

class YaleFBHTMLParser(HTMLParser):
  def __init__(self, f_out):
    super(YaleFBHTMLParser, self).__init__()
    self.model = FBStudentModel(f_out)
    self.student_div_depth = 0 # Number of inner divs incl the current student div
    self.n_students = 0
    self.div_classes = []

  def handle_starttag(self, tag, attrs):
    attrs = dict(attrs)

    # print("Start tag:", tag)
    # print("     attr:", attrs)

    if tag == 'div':
      div_classes = attrs.get('class')
      if div_classes:
        div_classes = div_classes.split()

      if 'student_container' in div_classes:
        self.student_div_depth = 1
        self.next_data = ''
        self.model.new_student()
        self.n_students += 1
      else:
        self.student_div_depth += 1
        self.div_classes = div_classes

    elif tag == 'img':
      _, _, img_id = attrs['src'].partition('=')
      if img_id != '0':
        self.model.add_attr('img', img_id)

  def handle_endtag(self, tag):
    # print("End tag  :", tag)
    if tag == 'div':
      self.next_data = ''
      self.student_div_depth -= 1

      if self.student_div_depth == 0:
        self.model.write_student()


  def handle_data(self, data):
    # print("Data     :", data)
    if 'student_year' in self.div_classes:
      if len(data) > 1: # student may not have grad year (if visiting international or on leave)
        self.model.add_attr('grad_year', '20' + data[1:]) # turn '21 into 2021 etc
    elif 'student_name' in self.div_classes:
      last_name, _, first_name = data.partition(',')
      self.model.add_attr('first_name', first_name)
      self.model.add_attr('last_name', last_name)
    elif 'student_info' in self.div_classes:
      if 'college' not in self.model.curr_student and data[-7:] == 'College':
        self.model.add_attr('college', data)
      elif 'email' not in self.model.curr_student and data[-9:] == '@yale.edu':
        self.model.add_attr('email', data)
      else:
        self.model.add_other(data)


def main():
  try:
    outfile = sys.argv[1]
    netid = sys.argv[2]
    password = sys.argv[3]
  except:
    print('Usage: python3 {} out_file.csv username password'.format(sys.argv[0]))
    sys.exit(1)
  
  s = requests.Session()
  login_params = {'username': netid,
                  'password': password,
                  'service': 'https://students.yale.edu/facebook/PhotoPageNew'}

  login_response = s.post('https://secure.its.yale.edu/cas/login', data=login_params)

  assert login_response.url[8:25] == 'students.yale.edu'
  print('Logged in')

  wait_random()
  yc_response = s.get('https://students.yale.edu/facebook/ChangeCollege?newOrg=Yale%20College')
  wait_random()
  
  with open(outfile, 'w') as f:
    parser = YaleFBHTMLParser(f)

    n_per_request = 200
    
    # There are < 6200 total entries in yale facebook
    for i in range(0,6400,n_per_request):
      
      parser.reset()

      params = {'currentIndex': i,
                'numberToGet': n_per_request}
      print('Getting i={}'.format(i))
      r = s.get('https://students.yale.edu/facebook/PhotoPageNew', params=params)

      lines = r.text.splitlines()
      students = lines[257]

      parser.feed(students)
      
      wait_random()

    print('Found {} students'.format(parser.n_students))


if __name__ == '__main__':
  main()
