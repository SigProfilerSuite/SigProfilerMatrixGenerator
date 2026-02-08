<h1> Installation </h1>

This section will help you set up the necessary software and packages required to run SigProfilerMatrixGenerator.

@[toc](Quick Links)
- [**Home**][1]
- [**Using** SigProfilerMatrixGenerator - **Input**][2]
- [**Using** SigProfilerMatrixGenerator - **Output**][3]
- [**Quick Start Example** for SigProfilerMatrixGenerator][4]    
- [**Currently** Supported Genomes][5]

----------

## Prerequisites ##
* Internet Connection
* [python][6] - v3.4+
* [pandas][7] - any version <br> *This will automatically be downloaded when you install SigProfilerMatrixGenerator.*
* [Wget][8] - v1.9 <br> 
* [SigProfilerPlotting][9] - latest version <br> *This will automatically be downloaded when you install SigProfilerMatrixGenerator. Installation of matplotlib is necessary for the plotting tool to be installed.*
* [Reference genomes][10] - latest version <br> *At least one of the reference genome files must be downloaded and installed on the system prior to use of the SigProfilerMatrixGenerator tool. These are not automatically downloaded when the tool is installed and require additional steps.*
<br><br>

## Upgrades ##
If there is an updated version of the tool that has been released, use the following command within Terminal or the Command Line: `pip install SigProfilerMatrixGenerator --upgrade`.
This will upgrade the tool to its latest version.
<br><br>

## Mac/Unix ##
For Mac/OSX systems, the use of a package manager like Conda is recommended to simplify environment setup.

To install SigProfilerMatrixGenerator, first check if you have python installed.

### python ###
Check that you have the required python version by opening Terminal (`⌘ + Space`, type terminal, and hit `return` to open the application) and entering the command:
```
$ python --version
```
By default, OSX systems come with a version of Python installed at `/usr/bin/python`. This system version of Python is currently Python 2. If you have multiple versions of Python installed, try the below command.
```
$ python3 --version
Python 3.7.3
```
Follow these instructions to download the most recent version of Python for your operating system if you do not have v3.4 or higher: [Python Installation][12].

Installation instructions for our recommended python package manager, Conda, through the Anaconda distribution can be found here: [Anaconda Installation][13].

*If you are installing python for the first time, pip is automatically installed in the same location.*

### pip ###
If necessary, separate installations of [pandas][14], [Wget][15], and [SigProfilerPlotting][16] can be achieved via [pip][17].

*pandas and SigProfilerPlotting are automatically installed with SigProfilerMatrixGenerator tool. Thus, you only need to install wget separately.*

Check if you have **pip** installed on your operating system and which version using by entering this command into Terminal:
```
$ pip --version
```
You should see an output similar to:
```
$ pip --version
pip 19.0.1 from /Library/Frameworks/SomeFilePath/
```
This tells you which version of pip is currently installed, and which version of Python it is set up to install packages for. This is especially helpful if you have more than one version of Python installed on your system. 

Follow the instructions here to download and install PIP for your operating system: [PIP Installation I][18], [PIP Installation II][19].

To install wget via pip, refer here: [wget pip][20].

To install wget via Conda, refer here: [wget conda][21]. 

### SigProfilerMatrixGenerator ###
Now that you've successfully downloaded all the required software, you can easily install **SigProfilerMatrixGenerator** using pip.

```
$ pip install SigProfilerMatrixGenerator
```

This will start running the installation process and once installation is complete, you should see the following output on the command line and these folders where your **python** framework and packages are saved.

![successful installation cmd line](https://files.osf.io/v1/resources/mc45g/providers/osfstorage/5c6dbb7982a395001ac890e8?mode=render =75%x)

![file structure](https://files.osf.io/v1/resources/mc45g/providers/osfstorage/5c6dc69e8d5d98001c302807?mode=render =75%x)
<br><br>

## Windows ##

To install SigProfilerMatrixGenerator, first check if you have python installed.

### python ###
By default, Windows systems do not come with Python installed. Check that you have the required python version by opening Command Prompt (`Win + R`, type cmd, and press `Enter` or press Ok) and entering the command:
```
> python --version
```
If you have multiple versions of Python installed, try the below command.
```
> python3 --version
Python 3.7.3
```
However if you know you have previously installed a version of python 3.4 or higher, and are getting the following error when trying to run python:
```
> python
'python' is not recognized as an internal or external command
```
Then python has not been added to the PATH environmental variable. To add it to the PATH, enter the following commands.

`$ setx PATH "%PATH%"; [path_to_python were .exe file is]"`

Follow these instructions to download the most recent version of Python for your operating system if you do not have v3.4 or higher: [Python Installation][23].

Make sure you check the box as indicated in the figure below.

![python install](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc77b1dd7dc3f00166d2ba0?mode=render =50%x)

*If you are installing python for the first time, pip will be automatically installed in the same location.*

### pip ###
If necessary, separate installations of [pandas][24], [Wget][25], and [SigProfilerPlotting][26] can be done via [pip][27].

*pandas and SigProfilerPlotting will automatically be installed when the SigProfilerMatrixGenerator tool is installed.*

Check if you have **pip** installed on your operating system and which version using by entering this command into Terminal:
```
$ pip --version
```
You should see an output similar to:
```
$ pip --version
pip 19.0.1 from c:\users\name\appdata\local\programs\python\pythonversion\lib\site-packages\pip
```
This tells you which version of pip is currently installed, and which version of Python it is set up to install packages for. This is especially helpful if you have more than one version of Python installed on your system. 

However if you know you have previously installed a version of pip, and are getting the following error when trying to run pip:
```
$ pip
'pip' is not recognized as an internal or external command
```
Then pip has not been added to the PATH environmental variable. To add it to the PATH, enter the following commands.

`$ setx PATH "%PATH%"; [path_to_python + \Scripts\]"`

Follow the instructions here to download and install PIP for your operating system: [PIP Installation I][28], [PIP Installation II][29].

### SigProfilerMatrixGenerator ###
Now that you've successfully downloaded all the required software, you can easily install **SigProfilerMatrixGenerator** using pip.

```
$ pip install SigProfilerMatrixGenerator
```
This will start running the installation process and once installation is complete, you should see the following output on the command line and these folders where your **python** framework and packages are saved.

![successful installation cmd line](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc7942500a81000195a59a1?mode=render =150%x)
<br><br>

## Reference Genome ##
Prior to use of the SigProfilerMatrixGenerator tool, the reference genome files need to be installed. Install your desired reference genome from the command line as follows:
```
$ python3
>> from SigProfilerMatrixGenerator import install as genInstall
>> genInstall.install('GRCh37', bash=True)
```
<br>
This example installs the custom human 37 assembly reference files but you can install any of the available [genome assemblies][30]. The installation will use bash commands as default. 

If the server has firewall in place, **wget** will not work. The `genInstall.install` command has an additional `rsync` parameter that must be set to **True** which acts as a wget equivalent.
```
$ python3
>> from SigProfilerMatrixGenerator import install as genInstall
>> genInstall.install('GRCh37', rsync=False)
```

The installation process saves the custom reference files for all chromosomes in the genome assembly so **~3 Gb** of storage must be available for the downloads for each genome. You can find all the downloaded reference files in the main SigProfilerMatrixGenerator folder. Because the custom files are so large, this step could take some time. <br>

![file structure](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc79461bbbd370017a16766?mode=render =75%x)



  [1]:  https://osf.io/s93d5/wiki/home/
  [2]: https://osf.io/s93d5/wiki/3.%20Using%20the%20Tool%20-%20Input/
  [3]: https://osf.io/s93d5/wiki/4.%20Using%20the%20Tool%20-%20Output/
  [4]: https://osf.io/s93d5/wiki/6.%20Quick%20Start%20Example/
  [5]: https://osf.io/s93d5/wiki/7.%20Currently%20Supported%20Genomes/
  [6]: https://www.python.org/downloads
  [7]: https://pandas.pydata.org/
  [8]: https://www.gnu.org/software/wget/
  [9]: https://osf.io/mc45g/
  [10]: https://osf.io/s93d5/wiki/7.%20Currently%20Supported%20Genomes/
  [12]: https://www.python.org/downloads
  [13]: https://www.anaconda.com/distribution/
  [14]: https://pandas.pydata.org/
  [15]: https://www.gnu.org/software/wget/
  [16]: https://osf.io/mc45g/
  [17]: https://pypi.org/project/pip/
  [18]: https://pypi.org/project/pip/
  [19]: https://ehmatthes.github.io/pcc/chapter_12/installing_pip.html
  [20]: https://pypi.org/project/wget/
  [21]: https://anaconda.org/anaconda/wget
  [22]: https://osf.io/s93d5/wiki/6.%20Currently%20Supported%20Genomes/
  [23]: https://www.python.org/downloads
  [24]: https://pandas.pydata.org/
  [25]: https://www.gnu.org/software/wget/
  [26]: https://github.com/AlexandrovLab/SigProfilerPlottingl
  [27]: https://pypi.org/project/pip/
  [28]: https://pypi.org/project/pip/
  [29]: https://ehmatthes.github.io/pcc/chapter_12/installing_pip.html
  [30]: https://osf.io/s93d5/wiki/6.%20Currently%20Supported%20Genomes/
