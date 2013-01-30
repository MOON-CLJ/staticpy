# staticpy

Static File Manager

## Installation
```bash
$ python setup.py install
or 
$ pip install -e git+https://github.com/MOON-CLJ/staticpy.git#egg=staticpy
```

## usage
```bash
$ staticpy pull
```

### Configuration
```json
{
    "staticpy": {
        "hostDict": {
            "code": "http://code.dapps.douban.com/",
            "gitcafe": "git://gitcafe.com/"
        },  
        "jquery/jquery": {
            "tag": "1.6.1",
            "build": [
                "npm install grunt-compare-size",
                "npm install grunt-git-authors",
                "grunt custom:-ajax"
            ],  
            "file": {
                "/src": "/temp_e/"
            }   
        }   
    }   
}
```
### 与istatic（https://github.com/mockee/istatic）

1，共同的实现目标，staticpy是python版本，istatic是nodejs的版本。

2，从实现的功能上来讲，目前staticpy多出几个功能，包括执行build、文件覆盖提示、配置文件采用json。以后staticpy和istatic的功能会保持绝大部分相同，后期我会同时投入istatic的开发。
