"""Geometry-only compensation for consistent mild row skew."""
from statistics import median

def aligned_centers(detections):
    if len(detections)<4: return detections
    height=median(float(d['height']) for d in detections)
    if height<=0: return detections
    slopes=[]
    for left in detections:
        candidates=[]
        for right in detections:
            dx=float(right['x_center'])-float(left['x_center'])
            dy=float(right['y_center'])-float(left['y_center'])
            if height*.35<dx<height*3 and abs(dy/dx)<=.36: candidates.append((dx,dy/dx))
        if candidates: slopes.append(min(candidates)[1])
    if len(slopes)<3: return detections
    slope=median(slopes)
    if abs(slope)<.03 or median(abs(x-slope) for x in slopes)>.08: return detections
    return [{**d,'y_center':float(d['y_center'])-slope*float(d['x_center'])} for d in detections]
