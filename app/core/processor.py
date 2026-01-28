import numpy as np
from PIL import Image

def calculate_image_stats(image_path, selection_rect):
    """
    Calculates statistics for the selected area of the image.
    selection_rect: tuple (x, y, w, h)
    """
    if not image_path or not selection_rect:
        return None

    x, y, w, h = selection_rect
    
    try:
        with Image.open(image_path) as img:
            img = img.convert('RGB')
            img_arr = np.array(img)
            
            # Clip coordinates
            img_h, img_w, _ = img_arr.shape
            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(img_w, x + w)
            y2 = min(img_h, y + h)
            
            if x1 >= x2 or y1 >= y2:
                return None

            crop = img_arr[y1:y2, x1:x2]
            
            # Basic stats
            avg_r = np.mean(crop[:, :, 0])
            avg_g = np.mean(crop[:, :, 1])
            avg_b = np.mean(crop[:, :, 2])

            # New stats: Median and StdDev
            median_r = np.median(crop[:, :, 0])
            median_g = np.median(crop[:, :, 1])
            median_b = np.median(crop[:, :, 2])
            
            std_r = np.std(crop[:, :, 0])
            std_g = np.std(crop[:, :, 1])
            std_b = np.std(crop[:, :, 2])

            # Unique colors
            pixels = crop.reshape(-1, 3)
            unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
            
            sorted_indices = np.argsort(-counts)
            unique_colors = unique_colors[sorted_indices]
            counts = counts[sorted_indices]

            # Histogram
            r_hist, _ = np.histogram(crop[:, :, 0], bins=256, range=(0, 256))
            g_hist, _ = np.histogram(crop[:, :, 1], bins=256, range=(0, 256))
            b_hist, _ = np.histogram(crop[:, :, 2], bins=256, range=(0, 256))
            
            return {
                'r': avg_r, 'g': avg_g, 'b': avg_b,
                'median_r': median_r, 'median_g': median_g, 'median_b': median_b,
                'std_r': std_r, 'std_g': std_g, 'std_b': std_b,
                'count': crop.shape[0] * crop.shape[1],
                'unique_colors': unique_colors,
                'counts': counts,
                'hist': (r_hist, g_hist, b_hist)
            }
    except Exception as e:
        print(f"Error processing image: {e}")
        return None
