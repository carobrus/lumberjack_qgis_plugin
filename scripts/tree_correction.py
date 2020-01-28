from qgis.core import (QgsApplication, QgsTask, QgsMessageLog, Qgis)
import gdal
import numpy as np
import scipy.ndimage as ndimage
import datetime
import time

from .. import Lumberjack


class TreeCorrectionTask(QgsTask):
    def __init__(self, dem_file, tree_mask_file, output_file, dilate_amount, smooth_it, lumberjack_instance):
        super().__init__("Tree Correction",  QgsTask.CanCancel)
        self.dem = dem_file
        self.tree_mask = tree_mask_file
        self.dilate_amount = dilate_amount
        self.lumberjack_instance = lumberjack_instance
        self.output_file = output_file
        self.smooth_it = smooth_it


    def run(self):
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(
                self.description()), Lumberjack.MESSAGE_CATEGORY, Qgis.Info)

            self.start_time_str = str(datetime.datetime.now())
            print("=" * 30 + self.start_time_str + "=" * 30)
            self.start_time = time.time()

            print("DEM: ", self.dem)
            print("Tree Mask: ", self.tree_mask)

            # Open DEM
            dataset_dem = gdal.Open(self.dem, gdal.GA_ReadOnly)
            dem_raster_band = dataset_dem.GetRasterBand(1)

            # Create a copy of the DEM
            memory_driver = gdal.GetDriverByName('GTiff')
            output_dataset = memory_driver.Create(
                self.output_file, dataset_dem.RasterXSize, dataset_dem.RasterYSize, 1, gdal.GDT_Int16)
            output_dataset.SetProjection(dataset_dem.GetProjectionRef())
            output_dataset.SetGeoTransform(dataset_dem.GetGeoTransform())
            outband = output_dataset.GetRasterBand(1)
            outband.WriteArray(dem_raster_band.ReadAsArray())
            outband.FlushCache()
            dataset_dem = None
            dem_raster_band = None
            output_dataset = None

            # Open mask
            dataset_mask = gdal.Open(self.tree_mask, gdal.GA_ReadOnly)
            mask_raster_band = dataset_mask.GetRasterBand(1)
            array_mask = np.array(dataset_mask.ReadAsArray())
            array_mask = np.array(array_mask - 1, dtype=bool)
            if self.dilate_amount != 0:
                array_mask = np.invert(array_mask)
                array_mask = ndimage.binary_dilation(array_mask, iterations=self.dilate_amount)
                array_mask = np.invert(array_mask)

            # Create mask File
            memory_driver = gdal.GetDriverByName('GTiff')
            output_dataset = memory_driver.Create(
                self.tree_mask[:-4] + "_no_data.tif", 
                dataset_mask.RasterXSize, dataset_mask.RasterYSize, 1, gdal.GDT_Byte)
            output_dataset.SetProjection(dataset_mask.GetProjectionRef())
            output_dataset.SetGeoTransform(dataset_mask.GetGeoTransform())
            outband = output_dataset.GetRasterBand(1)
            outband.WriteArray(array_mask)
            outband.FlushCache()
            output_dataset = None

            # Open copy file and mask
            dataset_dem = gdal.Open(self.output_file, gdal.GA_Update)
            dem_raster_band = dataset_dem.GetRasterBand(1)
            dataset_mask = gdal.Open(self.tree_mask[:-4] + "_no_data.tif", gdal.GA_ReadOnly)
            mask_raster_band = dataset_mask.GetRasterBand(1)

            result = gdal.FillNodata(
                targetBand = dem_raster_band, maskBand = mask_raster_band,
                maxSearchDist = 10, smoothingIterations = self.smooth_it
            )
            dataset_dem = None
            dataset_mask = None

            self.elapsed_time = time.time() - self.start_time
            print("Finished in {} seconds".format(str(self.elapsed_time)))

            if self.isCanceled():
                return False
            return True

        except Exception as e:
            self.exception = e
            return False


    def finished(self, result):
        if result:
            QgsMessageLog.logMessage(
                'Task "{name}" completed in {time} seconds\n' \
                'DEM file: {dem}\n' \
                'Tree Mask file: {tm}'.format(
                    name=self.description(), time=self.elapsed_time, dem=self.dem, tm=self.tree_mask),
                Lumberjack.MESSAGE_CATEGORY, Qgis.Success)

            self.lumberjack_instance.notify_tree_correction(
                self.start_time_str, self.output_file, self.elapsed_time)

        else:
            if self.exception is None:
                QgsMessageLog.logMessage(
                    'Task "{name}" not successful but without '\
                    'exception (probably the task was manually '\
                    'canceled by the user)'.format(name=self.description()),
                    Lumberjack.MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(name=self.description(), exception=self.exception),
                    Lumberjack.MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception


    def cancel(self):
        QgsMessageLog.logMessage(
            'Task "{name}" was canceled'.format(name=self.description()),
            Lumberjack.MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()
