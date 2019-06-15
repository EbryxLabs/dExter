## Usage
```
usage: script.py [-h] -profile PROFILE [-output OUTPUT]

optional arguments:
  -h, --help        show this help message and exit
  -profile PROFILE  profile to use for AWS access.
  -output OUTPUT    path / name of output file.
```
You can control which AWS account to use and what file to output the result in using **`-profile`** and **`-output`** parameters.
  
  Following is a sample output for the program.
```
{
  "eu-west-1": [
    {
      "id": "i-0a1234567890",
      "matches": {
        "Value": "ebMub2RlTmFtZSIgICAgIDoiVGVzdC1VU00tQW55d2hlcmUiLCJlbnZpcm9ubWVudCIgIDoicHJvZCIsImF2X3Byb2ZpbGUiICAgOiJzZW5zb3IiLCJhcl9yZXNwdXJkZXMiIDoid3lucyJ9"
      },
      "Value": {
        "<key-1>": "<value-1>",
        "<key-2>": "ebMub2RlTmFtZSIgICAgIDoiVGVzdC1VU00tQW55d2hlcmUiLCJlbnZpcm9ubWVudCIgIDoicHJvZCIsImF2X3Byb2ZpbGUiICAgOiJzZW5zb3IiLCJhcl9yZXNwdXJkZXMiIDoid3lucyJ9"
      }
    },
    {
      "id": "lt-01af5e9101501dcb8",
      "name": "lt-t3.large",
      "created_by": "arn:aws:iam::1234567890:user/john.smith@abc.com",
      "matches": [
        {
          "version": 4,
          "match": "<match-1>"
        },
        {
          "version": 2,
          "match": "<match-2>"
        },
        {
          "version": 1,
          "match": "<match-3>"
        },
        ...
      ]
    },
    ...
  ]
}
```
**`matches`** list shows what text has been expilictly caught by regexes. Following [regexes](https://github.com/dxa4481/truffleHogRegexes) are used to detect sensitive data from targeted content.  
**`id`** starting with `i-` refers to EC2 instances and their `userData` matches while **`id`** with prefix `lt-` refers to launch templates and respective sensitive catches.
