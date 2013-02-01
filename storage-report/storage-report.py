#!/usr/bin/python
import sys
import os
import pwd
import time
import optparse
import sqlite3

# Items to be filtered from file processing
filtered = '.'

# Global date calculations
currenttime = time.time()
dayinsecond = 86400

def main():
  usage = """
          First you will need to perform a search, creating a new database.
          %prog --db <DB Name> <Path to Search> 

          Once the database is created you can query it using the various built-in options
          %prog [options]

          Remember: Additional searches will add to an existing database if you do not 
          initialize the current one or specify a new database

          Using the --db option is well, optional. If you dont specify --db a database called 
          .sqlite-sa.db is created"""
  parser = optparse.OptionParser(usage) 
  parser.add_option('--db', dest='database', default='.sqlite-sa.db', help='Supply a name for the SQLite DB we will generate (In current directory)')
  parser.add_option('--initdb', action='store_true', default='False', help='Manually initialize the database')
  parser.add_option('--old', action='store_true', default='False', help='Show total amount of files / size of files seperated by range of days since last modification')
  parser.add_option('--list', dest='list', default='False', help='List full path of files for files older than number of days. Example: All files older than 100 days.')
  parser.add_option('--ext', action='store_true', default='False', help='Create a report showing counts of file extensions by date range')
  parser.add_option('--extnodate', action='store_true', default='False', help='Create a report showing counts of file extensions')
  parser.add_option('--archive', dest='archive', default='False', help='Directories that do not contain subdirectories or files more recent than the number of days given. Example: Show me directories that dont have files or folders newer than 100 days.')
  (options, args) = parser.parse_args()
  global database
  global conn
  global c
  database = options.database
  conn = sqlite3.connect(database)
  conn.text_factory = str
  c = conn.cursor()
  if options.initdb == True:
    try:
      create_database()
    except sqlite3.OperationalError:
      clear_database()
      create_database()
  elif options.old == True:
    FileOldFiles()
  elif options.list != 'False':
    age = options.list
    FileByDays(age)
  elif options.ext == True:
    FileByExt()
  elif options.extnodate == True:
    FileByExtNoDate()
  elif options.archive != 'False':
    age = options.archive
    FileArchive(age)
  elif len(args) >= 1:
    path_name = args[0]
    try:
      FileProc(path_name)
      c.close()
    except sqlite3.OperationalError:
      create_database()
      FileProc(path_name)
      c.close()
  else:
    print parser.print_help()
  c.close() 
    

def create_database():
  # Create a new database
  sql = 'CREATE TABLE files (ID integer primary key, MTIME integer,SIZE integer,USER text,PATH text, FILE text,EXTENSION text)'
  c.execute(sql)

def clear_database():
  # Clear the database
  sql = 'DROP TABLE files'
  c.execute(sql)

def FileProc(currentdir):
  # Process files in currentdir and add to a SQLite database
  currentdir = os.path.abspath(currentdir)
  filesindir = os.listdir(currentdir)

  for file in filesindir:
    if filtered not in currentdir:
      FILE = os.path.join(currentdir, file)

      if os.path.isfile(FILE) == True:
        extension = str.lower(os.path.splitext(FILE)[1])
        mtime = int(os.path.getmtime(FILE))
        size = int(os.path.getsize(FILE))
        path, filename = os.path.split(FILE)
        try:
          # Do not bomb out if you cant find the UID
          user = pwd.getpwuid(os.stat(FILE).st_uid).pw_name
        except KeyError:
          user = 'none'
        print 'Processing: ' + filename 
        c.execute('INSERT INTO files(mtime,size,user,path,file,extension) VALUES (?,?,?,?,?,?)', (mtime,size,user,path,filename,extension))
      elif os.path.islink(FILE) == False: 
        FileProc(FILE)
    conn.commit()

def FileOldFiles():
  # Query the SQLite database and show amount of files / size of files for a date range 
  sql = ('SELECT temp.range AS [day range], count(*) AS [number of files], SUM(size) AS [summed size] FROM ('
             'SELECT CASE '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 30 THEN "AAA" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 90 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 30 THEN "BBB" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 182 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 90 THEN "CCC" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 365 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 182 THEN "DDD" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 730 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 547 THEN "FFF" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 1095 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 730 THEN "GGG" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 1460 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 1095 THEN "HHH" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 1825 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 1460 THEN "III" '
             'ELSE "JJJ" END '
             'AS range, size FROM files'
           ') temp GROUP BY temp.range')
  c.execute(sql)
  query = c.fetchall()
  print ''
  print '{0:25} {1:15} {2:20}'.format('Days Old','#','Size of Files')
  print ''
  for x in query:
    size = str(x[2] / 1024) + ' Kb'
    numf = str(x[1])
    if x[0] == 'AAA':
      print '{0:25} {1:15} {2:20}'.format('0-30 Days Old',numf,size)
    elif x[0] == 'BBB':
      print '{0:25} {1:15} {2:20}'.format('30-90 Days Old',numf,size)
    elif x[0] == 'CCC':
      print '{0:25} {1:15} {2:20}'.format('90-182 Days Old',numf,size)
    elif x[0] == 'DDD':
      print '{0:25} {1:15} {2:20}'.format('182-365 Days Old',numf,size)
    elif x[0] == 'EEE':
      print '{0:25} {1:15} {2:20}'.format('365-547 Days Old',numf,size)
    elif x[0] == 'FFF':
      print '{0:25} {1:15} {2:20}'.format('547-730 Days Old',numf,size)
    elif x[0] == 'GGG':
      print '{0:25} {1:15} {2:20}'.format('730-1095 Days Old',numf,size)
    elif x[0] == 'HHH':
      print '{0:25} {1:15} {2:20}'.format('1095-1460 Days Old',numf,size)
    elif x[0] == 'III':
      print '{0:25} {1:15} {2:20}'.format('1460-1825 Days Old',numf,size)
    elif x[0] == 'JJJ':
      print '{0:25} {1:15} {2:20}'.format('Over Five Years Old',numf,size)

def FileByDays(age):
  # Print a list of files that are older than the time given
  age = int(currenttime - (int(age) * dayinsecond))
  c.execute('SELECT path,file FROM files WHERE path NOT IN (SELECT path FROM files WHERE mtime > (?))', (age,))
  query = c.fetchall()
  for x in query:
    print '{0:60}'.format(x[0] + '/' + x[1])

def FileByExt():
  # Create a report of files by extension seperated by date range
  sql = ('SELECT temp.range AS [day range], count(*) AS [number of files], extension AS [File Extensions], SUM(size) AS [summed size] FROM ('
             'SELECT CASE '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 30 THEN "AAA" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 90 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 30 THEN "BBB" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 182 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 90 THEN "CCC" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 365 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 182 THEN "DDD" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 730 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 547 THEN "FFF" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 1095 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 730 THEN "GGG" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 1460 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 1095 THEN "HHH" '
             'WHEN files.mtime > (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 1825 AND files.mtime <= (julianday("now") - 2440587.5)*86400.0 - 86400.0 * 1460 THEN "III" '
             'ELSE "JJJ" END '
             'AS range, extension, size FROM files'
           ') temp GROUP BY extension ORDER BY temp.range')
  c.execute(sql)
  query = c.fetchall()
  print ''
  print '{0:25} {1:13} {2:20} {3:50}'.format('Age of Files','Type','#','File Size')
  print ''
  for x in query:
    numf = str(x[1])
    type = str(x[2])
    size = str(x[3] / 1024) + ' Kb'
    if x[0] == 'AAA':
      print '{0:25} {1:13} {2:20} {3:50}'.format('0-30 Days Old',type,numf,size)
    elif x[0] == 'BBB':
      print '{0:25} {1:13} {2:20} {3:50}'.format('30-90 Days Old',type,numf,size)
    elif x[0] == 'CCC':
      print '{0:25} {1:13} {2:20} {3:50}'.format('90-182 Days Old',type,numf,size)
    elif x[0] == 'DDD':
      print '{0:25} {1:13} {2:20} {3:50}'.format('182-365 Days Old',type,numf,size)
    elif x[0] == 'EEE':
      print '{0:25} {1:13} {2:20} {3:50}'.format('365-547 Days Old',type,numf,size)
    elif x[0] == 'FFF':
      print '{0:25} {1:13} {2:20} {3:50}'.format('547-730 Days Old',type,numf,size)
    elif x[0] == 'GGG':
      print '{0:25} {1:13} {2:20} {3:50}'.format('730-1095 Days Old',type,numf,size)
    elif x[0] == 'HHH':
      print '{0:25} {1:13} {2:20} {3:50}'.format('1095-1460 Days Old',type,numf,size)
    elif x[0] == 'III':
      print '{0:25} {1:13} {2:20} {3:50}'.format('1460-1825 Days Old',type,numf,size)
    elif x[0] == 'JJJ':
      print '{0:25} {1:13} {2:20} {3:50}'.format('Over Five Years Old',type,numf,size)


def FileByExtNoDate():
  # Create a report of files by extension
  sql = ('SELECT count(*), extension, SUM(size) FROM files GROUP BY extension')
  c.execute(sql)
  query = c.fetchall()
  print ''
  print '{0:25} {1:20} {2:50}'.format('Type','#','File Size')
  print ''
  for x in query:
    numf = str(x[0])
    type = str(x[1])
    size = str(x[2] / 1024) + ' Kb'
    print '{0:25} {1:20} {2:50}'.format(type, numf, size)


def FileArchive(age):
  # Locate directories that are candidates for archival. 
  # We are looking for directories where all files within the directory are older than "age".
  age = int(currenttime - (int(age) * dayinsecond))
  c.execute('SELECT distinct path FROM files WHERE path NOT IN (SELECT distinct path FROM files WHERE mtime > (?))', (age,))
  query = c.fetchall()
  for x in query:
    print '{0:60}'.format(x[0])


if __name__ == "__main__":
  main()
