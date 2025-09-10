"""
Comprehensive tests for improved utility functions in modules.util

This test suite covers the enhanced functions with type hints, error handling,
and improved documentation.
"""

import unittest
import numpy as np
from PIL import Image
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import modules.flags
from modules import util


class TestUtilImprovements(unittest.TestCase):
    """Test suite for enhanced utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Create test images
        self.test_rgb_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        self.test_grayscale_image = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        self.test_rgba_image = np.random.randint(0, 255, (100, 100, 4), dtype=np.uint8)

    def test_erode_or_dilate_valid_inputs(self):
        """Test erode_or_dilate with valid inputs."""
        test_image = np.ones((50, 50), dtype=np.uint8) * 255
        
        # Test dilation (positive k)
        dilated = util.erode_or_dilate(test_image, 3)
        self.assertEqual(dilated.shape, test_image.shape)
        
        # Test erosion (negative k)
        eroded = util.erode_or_dilate(test_image, -2)
        self.assertEqual(eroded.shape, test_image.shape)
        
        # Test no change (k=0)
        unchanged = util.erode_or_dilate(test_image, 0)
        np.testing.assert_array_equal(unchanged, test_image)

    def test_erode_or_dilate_invalid_inputs(self):
        """Test erode_or_dilate with invalid inputs."""
        with self.assertRaises(ValueError):
            util.erode_or_dilate("not_an_array", 2)

    def test_resample_image_valid_inputs(self):
        """Test resample_image with valid inputs."""
        result = util.resample_image(self.test_rgb_image, 200, 150)
        self.assertEqual(result.shape, (150, 200, 3))

    def test_resample_image_invalid_dimensions(self):
        """Test resample_image with invalid dimensions."""
        with self.assertRaises(ValueError):
            util.resample_image(self.test_rgb_image, -100, 50)
        
        with self.assertRaises(ValueError):
            util.resample_image(self.test_rgb_image, 100, 0)

    def test_resize_image_mode_0(self):
        """Test resize_image with mode 0 (stretch)."""
        result = util.resize_image(self.test_rgb_image, 200, 150, resize_mode=0)
        self.assertEqual(result.shape, (150, 200, 3))

    def test_resize_image_mode_1(self):
        """Test resize_image with mode 1 (maintain aspect ratio, crop)."""
        result = util.resize_image(self.test_rgb_image, 200, 150, resize_mode=1)
        self.assertEqual(result.shape, (150, 200, 3))

    def test_resize_image_mode_2(self):
        """Test resize_image with mode 2 (maintain aspect ratio, pad)."""
        result = util.resize_image(self.test_rgb_image, 200, 150, resize_mode=2)
        self.assertEqual(result.shape, (150, 200, 3))

    def test_resize_image_invalid_mode(self):
        """Test resize_image with invalid resize mode."""
        with self.assertRaises(ValueError):
            util.resize_image(self.test_rgb_image, 100, 100, resize_mode=5)

    def test_resize_image_invalid_dimensions(self):
        """Test resize_image with invalid dimensions."""
        with self.assertRaises(ValueError):
            util.resize_image(self.test_rgb_image, -100, 100)

    def test_get_shape_ceil_valid_inputs(self):
        """Test get_shape_ceil with valid inputs."""
        result = util.get_shape_ceil(100, 100)
        self.assertIsInstance(result, float)
        self.assertGreater(result, 0)

    def test_get_shape_ceil_invalid_inputs(self):
        """Test get_shape_ceil with invalid inputs."""
        with self.assertRaises(ValueError):
            util.get_shape_ceil(-100, 100)
        
        with self.assertRaises(ValueError):
            util.get_shape_ceil(100, 0)

    def test_get_image_shape_ceil_valid_input(self):
        """Test get_image_shape_ceil with valid image."""
        result = util.get_image_shape_ceil(self.test_rgb_image)
        self.assertIsInstance(result, float)
        self.assertGreater(result, 0)

    def test_get_image_shape_ceil_invalid_input(self):
        """Test get_image_shape_ceil with invalid image."""
        with self.assertRaises(ValueError):
            util.get_image_shape_ceil("not_an_array")
        
        with self.assertRaises(ValueError):
            util.get_image_shape_ceil(np.array([1, 2, 3]))  # 1D array

    def test_set_image_shape_ceil_valid_inputs(self):
        """Test set_image_shape_ceil with valid inputs."""
        target_ceil = 128.0
        result = util.set_image_shape_ceil(self.test_rgb_image, target_ceil)
        self.assertEqual(len(result.shape), 3)

    def test_set_image_shape_ceil_invalid_inputs(self):
        """Test set_image_shape_ceil with invalid inputs."""
        with self.assertRaises(ValueError):
            util.set_image_shape_ceil(self.test_grayscale_image, 128.0)  # 2D array
        
        with self.assertRaises(ValueError):
            util.set_image_shape_ceil(self.test_rgb_image, -128.0)  # Negative ceiling

    def test_HWC3_rgb_input(self):
        """Test HWC3 with RGB input."""
        result = util.HWC3(self.test_rgb_image)
        np.testing.assert_array_equal(result, self.test_rgb_image)

    def test_HWC3_grayscale_input(self):
        """Test HWC3 with grayscale input."""
        result = util.HWC3(self.test_grayscale_image)
        self.assertEqual(result.shape, (100, 100, 3))
        # Check that all three channels are identical
        np.testing.assert_array_equal(result[:, :, 0], result[:, :, 1])
        np.testing.assert_array_equal(result[:, :, 1], result[:, :, 2])

    def test_HWC3_rgba_input(self):
        """Test HWC3 with RGBA input."""
        result = util.HWC3(self.test_rgba_image)
        self.assertEqual(result.shape, (100, 100, 3))

    def test_HWC3_invalid_input(self):
        """Test HWC3 with invalid inputs."""
        # Test non-numpy array
        with self.assertRaises(ValueError):
            util.HWC3("not_an_array")
        
        # Test wrong dtype
        wrong_dtype = np.random.randint(0, 255, (100, 100, 3), dtype=np.int32)
        with self.assertRaises(ValueError):
            util.HWC3(wrong_dtype)
        
        # Test invalid number of channels
        invalid_channels = np.random.randint(0, 255, (100, 100, 5), dtype=np.uint8)
        with self.assertRaises(ValueError):
            util.HWC3(invalid_channels)

    def test_performance_with_large_images(self):
        """Test performance with larger images."""
        large_image = np.random.randint(0, 255, (1000, 1000, 3), dtype=np.uint8)
        
        # This should complete without timeout
        result = util.resize_image(large_image, 500, 500)
        self.assertEqual(result.shape, (500, 500, 3))

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test minimal size images
        tiny_image = np.random.randint(0, 255, (2, 2, 3), dtype=np.uint8)
        result = util.resize_image(tiny_image, 100, 100)
        self.assertEqual(result.shape, (100, 100, 3))
        
        # Test square to non-square resize
        square_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        result = util.resize_image(square_image, 200, 100)
        self.assertEqual(result.shape, (100, 200, 3))


if __name__ == '__main__':
    unittest.main()