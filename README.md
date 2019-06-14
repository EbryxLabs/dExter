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
      "match": "ebMub2RlTmFtZSIgICAgIDoiVGVzdC1VU00tQW55d2hlcmUiLCJlbnZpcm9ubWVudCIgIDoicHJvZCIsImF2X3Byb2ZpbGUiICAgOiJzZW5zb3IiLCJhcl9yZXNwdXJkZXMiIDoid3lucyJ9",
      "value": {
        "<key-1>": "<value-1>",
        "<key-2>": "ebMub2RlTmFtZSIgICAgIDoiVGVzdC1VU00tQW55d2hlcmUiLCJlbnZpcm9ubWVudCIgIDoicHJvZCIsImF2X3Byb2ZpbGUiICAgOiJzZW5zb3IiLCJhcl9yZXNwdXJkZXMiIDoid3lucyJ9"
      }
    }
  ]
}
```
**`match`** field shows what text has been expilictly caught by regexes.  
**`value`** field shows the entire base64 decoded `userData` of an instance, in this case of ID `i-0a1234567890`.
