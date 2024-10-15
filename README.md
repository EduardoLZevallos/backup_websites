# backup_websites

## running script
```
source bin/activate # activate venv 
python3.12 backup_website.py  
```
Running the script creatings following directories:
* tortillaconsal.com (minority of files)
* www.tortillaconsal.com (majority of files)

There maybe some files in tortillaconsal.com but not in www.tortillaconsal.com, to check 
these differences use 
```
diff -r tortillaconsal.com www.tortillaconsal.com | grep 'Only in tortillaconsal.com'
```
Added logic to handle the consoldiation of redundant tortilla con sal directory

## job details
in total backuping up the website is about 13.5gb and it took around 3 hours to run the entire script

## recent runs
* complete list of files uploaded to s3 bucket see tortilla_con_sal_files_backed_up_10.14.24.txt