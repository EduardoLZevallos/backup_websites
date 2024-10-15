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
I have logic that merges and removes redundant directory

## job details
in total backuping up the website is about 13.5gb and it took around 3 hours to run the entire script

## for a complete list of files uploaded to s3 bucket see file tortilla_con_sal_files_backed_up.txt updated as of 10/14/2024