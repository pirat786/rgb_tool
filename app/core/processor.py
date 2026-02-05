import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
import os

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
            
            # Basic stats (RGB)
            avg_r = np.mean(crop[:, :, 0])
            avg_g = np.mean(crop[:, :, 1])
            avg_b = np.mean(crop[:, :, 2])

            median_r = np.median(crop[:, :, 0])
            median_g = np.median(crop[:, :, 1])
            median_b = np.median(crop[:, :, 2])
            
            std_r = np.std(crop[:, :, 0])
            std_g = np.std(crop[:, :, 1])
            std_b = np.std(crop[:, :, 2])

            # HSV Stats
            hsv_crop = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
            avg_h = np.mean(hsv_crop[:, :, 0])
            avg_s = np.mean(hsv_crop[:, :, 1])
            avg_v = np.mean(hsv_crop[:, :, 2])
            
            stats_hsv = {
                'avg_h': avg_h, 'avg_s': avg_s, 'avg_v': avg_v,
                'median_h': np.median(hsv_crop[:, :, 0]), 
                'median_s': np.median(hsv_crop[:, :, 1]), 
                'median_v': np.median(hsv_crop[:, :, 2]),
                'std_h': np.std(hsv_crop[:, :, 0]), 
                'std_s': np.std(hsv_crop[:, :, 1]), 
                'std_v': np.std(hsv_crop[:, :, 2])
            }

            # LAB Stats
            lab_crop = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB)
            avg_l = np.mean(lab_crop[:, :, 0])
            avg_a = np.mean(lab_crop[:, :, 1])
            avg_bb = np.mean(lab_crop[:, :, 2]) # 'b' matches RGB 'b', so use 'bb' for LAB-b
            
            stats_lab = {
                'avg_l': avg_l, 'avg_a': avg_a, 'avg_b': avg_bb,
                'median_l': np.median(lab_crop[:, :, 0]),
                'median_a': np.median(lab_crop[:, :, 1]),
                'median_b': np.median(lab_crop[:, :, 2]),
                'std_l': np.std(lab_crop[:, :, 0]),
                'std_a': np.std(lab_crop[:, :, 1]),
                'std_b': np.std(lab_crop[:, :, 2])
            }

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
                'hsv': stats_hsv,
                'lab': stats_lab,
                'count': crop.shape[0] * crop.shape[1],
                'unique_colors': unique_colors,
                'counts': counts,
                'hist': (r_hist, g_hist, b_hist)
            }
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def calculate_line_profile(image_path, line_coords):
    """
    Calculates RGB profile along a line.
    line_coords: tuple (x1, y1, x2, y2)
    """
    if not image_path or not line_coords:
        return None

    x1, y1, x2, y2 = line_coords
    
    try:
        with Image.open(image_path) as img:
            img = img.convert('RGB')
            img_arr = np.array(img)
            
            h, w, _ = img_arr.shape
            
            # Calculate number of points based on distance
            dist = int(np.hypot(x2 - x1, y2 - y1))
            if dist == 0: return None
            
            num_points = dist
            
            # Generate coordinates
            x_values = np.linspace(x1, x2, num_points)
            y_values = np.linspace(y1, y2, num_points)
            
            # Sample using nearest neighbor (integer casting)
            # Clip coords to be safe
            x_idx = np.clip(np.round(x_values).astype(int), 0, w - 1)
            y_idx = np.clip(np.round(y_values).astype(int), 0, h - 1)
            
            # Extract
            r = img_arr[y_idx, x_idx, 0]
            g = img_arr[y_idx, x_idx, 1]
            b = img_arr[y_idx, x_idx, 2]
            
            return {'r': r, 'g': g, 'b': b}
            
    except Exception as e:
        print(f"Error calculating profile: {e}")
        return None

def calculate_grid_stats(image_path, cell_size):
    """
    Calculates statistics for every cell in a grid over the image.
    Returns a list of dictionaries with coordinates and stats.
    """
    if not image_path or cell_size <= 0:
        return []

    results = []
    
    try:
        with Image.open(image_path) as img:
            img = img.convert('RGB')
            img_arr = np.array(img)
            
            h, w, _ = img_arr.shape
            
            # Iterate through grid
            for y in range(0, h, cell_size):
                for x in range(0, w, cell_size):
                    # Define cell boundaries
                    x2 = min(x + cell_size, w)
                    y2 = min(y + cell_size, h)
                    
                    # Skip partial cells (if not full size)
                    if (x2 - x) != cell_size or (y2 - y) != cell_size:
                        continue
                    
                    # Extract crop
                    crop = img_arr[y:y2, x:x2]
                    
                    if crop.size == 0:
                        continue
                        
                    # Calculate Stats (Simplified for batch processing)
                    # We focus on what's requested: "coordinate and data"
                    # Average RGB is the most useful "data"
                    
                    avg_r = np.mean(crop[:, :, 0])
                    avg_g = np.mean(crop[:, :, 1])
                    avg_b = np.mean(crop[:, :, 2])
                    
                    # Determine predominant color or other metric?
                    # For now just Averages and Standard Deviations
                    
                    results.append({
                        'x': x,
                        'y': y,
                        'avg_r': avg_r,
                        'avg_g': avg_g,
                        'avg_b': avg_b,
                        'std_r': np.std(crop[:, :, 0]),
                        'std_g': np.std(crop[:, :, 1]),
                        'std_b': np.std(crop[:, :, 2])
                    })
                    
        return results
            
    except Exception as e:
        print(f"Error calculating grid stats: {e}")
        return []

def create_annotated_image(image_path, results, cell_size, output_path):
    """
    Creates a copy of the image with grid and coordinates drawn on it.
    """
    try:
        with Image.open(image_path) as img:
            img = img.convert('RGB')
            draw = ImageDraw.Draw(img)
            
            # Try to load a font
            try:
                # Adjust font size based on cell size - make it smaller
                font_size = max(8, int(cell_size / 6))
                font = ImageFont.truetype("arial.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()
            
            img_w, img_h = img.size

            for r in results:
                x, y = r['x'], r['y']
                
                # Calculate dimensions dynamically since we removed them from results
                w = min(cell_size, img_w - x)
                h = min(cell_size, img_h - y)
                
                # Draw rect
                draw.rectangle([x, y, x+w, y+h], outline="cyan", width=2)
                
                # Draw text split in two lines to save width
                text_x = str(x)
                text_y = str(y)
                
                # Helper to get size
                def get_size(txt):
                    try:
                        bbox = draw.textbbox((0, 0), txt, font=font)
                        return bbox[2] - bbox[0], bbox[3] - bbox[1]
                    except AttributeError:
                        return draw.textsize(txt, font=font)

                w_x, h_x = get_size(text_x)
                w_y, h_y = get_size(text_y)
                
                total_h = h_x + h_y + 2 # 2px spacing

                # Center X coordinate
                tx_x = x + (w - w_x) / 2
                ty_x = y + (h - total_h) / 2
                
                # Center Y coordinate below X
                tx_y = x + (w - w_y) / 2
                ty_y = ty_x + h_x + 2
                
                # Draw X
                draw.text((tx_x+1, ty_x+1), text_x, font=font, fill="black")
                draw.text((tx_x, ty_x), text_x, font=font, fill="yellow")

                # Draw Y
                draw.text((tx_y+1, ty_y+1), text_y, font=font, fill="black")
                draw.text((tx_y, ty_y), text_y, font=font, fill="yellow")
                
            img.save(output_path)
            return True
    except Exception as e:
        print(f"Error creating annotated image: {e}")
        return False
