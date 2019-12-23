#!/usr/bin/env python

#%module
#% description: Compute asm, contrast, var, idm and entr for each band of a TIFF file
#% keyword: raster
#% keyword: haralick
#% keyword: features
#%end

#%option G_OPT_M_DIR
#% key: input
#% type: string
#% required : yes
#%end

#%option
#% key: size
#% type: integer
#% required: yes
#% multiple: no
#% key_desc: value
#% description: The size of moving window (odd and >= 3)
#% answer: 3
#%end

#%option
#% key: distance
#% type: integer
#% required: yes
#% multiple: no
#% key_desc: value
#% label: The distance between two samples (>= 1)
#% description: The distance must be smaller than the size of the moving window
#% answer: 1
#%end

#%option
#% key: categories
#% type: integer
#% description: Number of categories to rescale/recode the image
#% answer: 255
#% required : yes
#%end

#%flag
#% key: r
#% description: Rescales instead of recoding the image
#%end

#%flag
#% key: d
#% description: Calculate textures of DEM instead of Landsat Images
#%end


import sys
import grass.script as gscript
from grass.pygrass.modules import Module, ParallelModuleQueue
from copy import deepcopy
from osgeo import gdal
import os
import time
import atexit


def main():
	options,flags = gscript.parser()
	input_dir = options['input']
	sizeMovingWindow = options['size']
	distance = options['distance']
	numCategories = options['categories']
	recode = flags['r']
	use_dem = flags['d']

	start_time = time.time()

	try:
		##Validate parameters
		if (int(sizeMovingWindow) % 2 == 0) or (int(sizeMovingWindow) < 2) or (int(distance) >= int(sizeMovingWindow)) or (int(numCategories) > 255):
			raise
	except:
		print "Size of moving windows must be odd and >=3."
		print "The distance must be smaller than the size of the moving window."
		print "The raster map cannot have more than 255 categories."
	else:
		gscript.run_command('g.mapset', mapset='PERMANENT')

		# r=root, d=directories, f = files
		for r, d, f in os.walk(input_dir):
			print "Checking directory: ", r
			count = 1
			for file in f:
				full_path = os.path.join(r, file)
				if (full_path[-7:-4] == "reg") and (not use_dem):
					gscript.run_command('g.proj', flags='c', georef=full_path)
					gscript.run_command('r.in.gdal', flags='k', input=full_path, output='region_raster', overwrite=True)
					gscript.run_command('g.region', raster='region_raster', overwrite=True)

				if (full_path[-7:-4] == "dem") and (use_dem):
					print "DEM: ", full_path

					gscript.run_command('g.proj', flags='c', georef=full_path)
					gscript.run_command('r.in.gdal', flags='k', input=full_path, output='inputBands.1', overwrite=True)
					## Manages the boundary definitions for the geographic region.
					gscript.run_command('g.region', raster='inputBands.1')
					output_file = full_path[:-4] + "_text.tif"
					print "Output File to be created: ", output_file
					count += 1

				if (full_path[-9:-5] == "band") and (not use_dem):
					if (count == 1):
						output_file = full_path[:-12] + "text.tif"
						print "Output File to be created: ", output_file
					gscript.run_command('r.in.gdal', flags='k', input=full_path, output='inputBands.{}'.format(count), overwrite=True)
					count += 1

			if (count == 8) or (count == 2):

				bandCount = count-1
				rasterName = []

				inputRescale  = "inputBands.{}"
				outputRescale = "bandsRescale.{}"

				if recode == False:
					for band in range(1,bandCount+1):
						rules = gscript.read_command('r.quantile', flags='r', input=inputRescale.format(band), quantiles=numCategories, overwrite=True, quiet=True)
						print "Recoding raster map {}".format(band)
						gscript.write_command('r.recode', input=inputRescale.format(band), output=outputRescale.format(band), rules='-', overwrite=True, stdin=rules)
				else:
					for band in range(1,bandCount+1):
						gscript.run_command('r.rescale', input=inputRescale.format(band), output=outputRescale.format(band), to='1,'+numCategories, overwrite=True)

				outputTexture = "band.{}"

				queue = ParallelModuleQueue(nprocs=4)
				texture = Module('r.texture', flags='n', method=['asm','contrast','var','idm','entr'], size=sizeMovingWindow, distance=distance, overwrite=True, run_=False)

				for band in range(1,bandCount+1):
					m = deepcopy(texture)(input=outputRescale.format(band), output=outputTexture.format(band))
					queue.put(m)
				queue.wait()

				for band in range(1,bandCount+1):
					rasterName.extend([outputTexture.format(band)+'_ASM', outputTexture.format(band)+'_Contr',outputTexture.format(band)+'_Var',outputTexture.format(band)+'_IDM',outputTexture.format(band)+'_Entr'])
					## Generate group to export the tiff image
					groupInput = outputTexture.format(band)+'_ASM,'+outputTexture.format(band)+'_Contr,'+outputTexture.format(band)+'_Var,'+outputTexture.format(band)+'_IDM,'+outputTexture.format(band)+'_Entr'
					gscript.run_command('i.group', group='outFileBands', input=groupInput, quiet=True)

				## Creating tiff image
				gscript.run_command('r.out.gdal', flags='cm', input='outFileBands', output=output_file, format='GTiff', type='Float32', overwrite=True, verbose=True)

				print "Finished creating features"
				print "Renaming raster bands"

				src_ds = gdal.Open(output_file)
				for band in range(src_ds.RasterCount):
					band += 1
					src_ds.GetRasterBand(band).SetDescription(rasterName[band-1])

		elapsed_time = time.time() - start_time
		print "Finished in: ", elapsed_time, " seconds"


def cleanup():
	## Remove raster maps from group
	cf = gscript.find_file(name='outFileBands', element='group')
	if not cf['fullname'] == '':
		gscript.run_command('g.remove', flags='f', type='group', name='outFileBands', quiet=True)

	cf = gscript.find_file(name='inputBands', element='group')
	if not cf['fullname'] == '':
		gscript.run_command('g.remove', flags='f', type='group', name='inputBands', quiet=True)

	## Remove raster maps
	cf = gscript.find_file(name='region_raster', element='cell')
	if not cf['fullname'] == '':
		gscript.run_command('g.remove', flags='f', type='raster', pattern='region_raster', quiet=True)

	cf = gscript.find_file(name='band.1_ASM', element='cell')
	if not cf['fullname'] == '':
		gscript.run_command('g.remove', flags='f', type='raster', pattern='band.*', quiet=True)

	cf = gscript.find_file(name='bandsRescale.1', element='cell')
	if not cf['fullname'] == '':
		gscript.run_command('g.remove', flags='f', type='raster', pattern='bandsRescale.*', quiet=True)

	cf = gscript.find_file(name='inputBands.1', element='cell')
	if not cf['fullname'] == '':
		gscript.run_command('g.remove', flags='f', type='raster', pattern='inputBands.*', quiet=True)


if __name__ == '__main__':
	atexit.register(cleanup)
	main()
