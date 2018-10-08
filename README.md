## Pre-requisites

Get your Stats API credentials here:
https://faq.revcontent.com/customer/en/portal/articles/2702263-stats-api-documentation-and-setup-advertisers-publishers-


## Installation & Run

1. Install the packages in requirements.txt (ideally in a virtualenv)
```
virtualenv -p python3.6 virtualenv
virtualenv/bin/pip install -r requirements.txt
```

2. Before running the script, make sure to export these env vars:
```
export REVCONTENT_CLIENT_ID=replacevaluehere
export REVCONTENT_CLIENT_SECRET=replacevaluehere
```

3. Run script
```
. virtualenv/bin/activate && python get_revcontent_stats.py
```
