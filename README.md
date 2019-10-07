# Lumberjack <img align="right" width="45" height="45" src="icon.png" alt="Lumberjack icon">

A qgis plugin to calculate features of images, classify and remove trees out of elevation maps

<!-- ## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system. -->


### Prerequisites

<!--- What things you need to install the software and how to install them -->
* [QGIS Desktop 3 with GRASS](https://www.qgis.org/) - A Free and Open Source Geographic Information System
* Python 3
* scipy
* numpy

<!-- ```
Give examples
``` -->

### Installation of python libraries

Open the OsGeo shell (it gets installed with QGIS on a Windows machine) and type:
```bash
py3_env.bat
pip install *name-of-library*
```

## Installation

You can download the repository and add it along with the other python plugins. By default this is located in:
`C:\OSGeo4W64\apps\qgis\python\plugins` <br/>&nbsp;&nbsp;&nbsp;&nbsp;
If you are not sure about the location, you can:
* Download the repository as a .zip.
* In QGIS go to *Plugins > Manage and Install Plugins > Install from ZIP* and browse the .zip file.
* Click on *Intall Plugin* and accept the security check.

After this, you should be able to see the plugin among the installed ones.

> Do not forget to activate the plugin selecting the checkbox at *Plugins > Manage and Install Plugins > All*. You should be able to see the plugin at the plugins menu ( <kbd>alt</kbd> + <kbd>p</kbd> ).


## How to Use
...

Directories have to keep certain a format. Each directory hold folders with places. Each place should have a .tiff file defining the extension to process and the Landsat 8 images as downloaded from USGS. Also, each place might have features to apply to that place (e.g. textures of the DEM).<br/>&nbsp;&nbsp;&nbsp;&nbsp;
If additional features are intended to be consider for an image, each image folder has to contain a file with the same suffix.<br/>&nbsp;&nbsp;&nbsp;&nbsp;
An example directory:

```
C:\USERS\USER\DOCUMENTS\TRAINING
├───GralVillegas
│   │   demGralVillegasRescale-textures.tif
│   │   GralVillegas-ext.tif
│   │   ...
│   │   GralVillegas_roi.shp
│   │   GralVillegas_roi.shx
│   │
│   ├───LC082280842017113001T1-SC20190815123416
│   │       LC08_L1TP_228084_20171130_20171207_01_T1.xml
│   │       LC08_L1TP_228084_20171130_20171207_01_T1_ANG.txt
│   │       LC08_L1TP_228084_20171130_20171207_01_T1_MTL.txt
│   │       ...
│   │       LC08_L1TP_228084_20171130_20171207_01_T1_sr_band7.tif
│   │       LC08_L1TP_228084_20171130_20171207_01_T1_text.tif
│   │
│   └───LC082280842019071501T1-SC20190815133929
│           LC08_L1TP_228084_20190715_20190721_01_T1.xml
│           LC08_L1TP_228084_20190715_20190721_01_T1_ANG.txt
│           LC08_L1TP_228084_20190715_20190721_01_T1_MTL.txt
│           ...
│           LC08_L1TP_228084_20190715_20190721_01_T1_sr_band7.tif
│           LC08_L1TP_228084_20190715_20190721_01_T1_text.tif
│
└───LasFlores
    │   demLasFloresRescale-textures.tif
    │   LasFlores-ext.tif
    │   ...
    │   LasFlores_roi.shp
    │   LasFlores_roi.shx
    │
    └───LC082250852017082101T1-SC20190815115812
            LC08_L1TP_225085_20170821_20170911_01_T1.xml
            LC08_L1TP_225085_20170821_20170911_01_T1_ANG.txt
            LC08_L1TP_225085_20170821_20170911_01_T1_MTL.txt
            ...
            LC08_L1TP_225085_20170821_20170911_01_T1_sr_band7.tif
            LC08_L1TP_225085_20170821_20170911_01_T1_text.tif
```

<!-- # Lumberjack ![alt text](https://github.com/carobrus/qgis_python_plugin/blob/master/icon.jpg) -->

<!--
## Running

Explain how to run the automated tests for this system -->

<!-- ### Break down into end to end tests

Explain what these tests test and why

```
Give an example
``` -->

<!--
## Built With

* [Dropwizard](http://www.dropwizard.io/1.0.2/docs/) - The web framework used
* [Maven](https://maven.apache.org/) - Dependency Management
* [ROME](https://rometools.github.io/rome/) - Used to generate RSS Feeds -->


<!-- ## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags).  -->


<!-- ## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details -->

<!-- ## Acknowledgments

* Hat tip to anyone whose code was used
* Inspiration
* etc -->
