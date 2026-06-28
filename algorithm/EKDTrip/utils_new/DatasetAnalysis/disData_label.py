import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from geopy.distance import geodesic
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from scipy.optimize import curve_fit

import pandas as pd

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def gaussian(x, a, b, c):
    return a * np.exp(-(x - b)**2 / (2 * c**2))  


def fit_polynomial_trend(distance_to_end, degree=2):
    positions = np.arange(len(distance_to_end)).reshape(-1, 1)
    poly = PolynomialFeatures(degree=degree)
    X_poly = poly.fit_transform(positions)
    
    model = LinearRegression()
    model.fit(X_poly, distance_to_end)
    distance_pred = model.predict(X_poly)
    
    mse = mean_squared_error(distance_to_end, distance_pred)
    
    return model, distance_pred, mse


def fit_gaussian_trend(distance_to_end):
    positions = np.arange(len(distance_to_end))
    
    distance_to_end[distance_to_end == 0.0] = 1e-6
    
    
    initial_guess = [max(distance_to_end), np.mean(positions), 1]
    
   
    try:
        params, _ = curve_fit(gaussian, positions, distance_to_end, p0=initial_guess)
        fitted_curve = gaussian(positions, *params)
    except RuntimeError as e:
        
        fitted_curve = None
    
    return fitted_curve


def calculate_trend_label_from_fitted_curve(distance_to_end, predicted_distance, traj_id, fitted_curve=None):
  
    derivative = np.diff(predicted_distance)
    
    
    increasing_count = np.sum(derivative > 0)
    decreasing_count = np.sum(derivative < 0)
   
    mse = mean_squared_error(distance_to_end, predicted_distance)
    
    if mse > 100000:  
        print("large mse:", traj_id)
        return 'irregular'
    
    if increasing_count == len(derivative):
        return 'increasing'  
    elif decreasing_count == len(derivative):
        return 'decreasing'  
       
    elif fitted_curve is not None:
        
        return 'increasing_then_decreasing'  
    else:
        return 'irregular'  


def get_trend_labels(df_sorted):
    trend_labels = []
    for traj_id, group in df_sorted.groupby('trajID'):
        distance_to_end = group['distance_to_end'].values

        
        if len(distance_to_end) > 3 and distance_to_end[-1] == 0.0:
            distance_to_end_new = distance_to_end[:-1]
        else:
            distance_to_end_new = distance_to_end
        
     
        model, predicted_distance, mse = fit_polynomial_trend(distance_to_end, degree=2)
        
        
        trend_label = calculate_trend_label_from_fitted_curve(distance_to_end, predicted_distance, traj_id)
        
        
        if trend_label == 'irregular':
            fitted_curve = fit_gaussian_trend(distance_to_end)
            trend_label = calculate_trend_label_from_fitted_curve(distance_to_end, predicted_distance, traj_id, fitted_curve=fitted_curve)
        
        _, predicted_distance_new, _ = fit_polynomial_trend(distance_to_end_new, degree=2)
        
        trend_label_new = calculate_trend_label_from_fitted_curve(distance_to_end_new, predicted_distance_new, traj_id)
        
        if trend_label_new == 'irregular':
            fitted_curve_new = fit_gaussian_trend(distance_to_end_new)
            trend_label_new = calculate_trend_label_from_fitted_curve(distance_to_end_new, predicted_distance_new, traj_id, fitted_curve=fitted_curve_new)

        if (trend_label_new != trend_label):
            print("traj_ID:", traj_id, "original label:", trend_label, "new label:", trend_label_new)
        trend_labels.append((traj_id, trend_label))
    
    return trend_labels


df = pd.read_csv('./dataset/dataAnaly/disAnaly/trajectory_distances_TKY_split200_temp.csv')


df_sorted = df.sort_values(by=['trajID', 'POI_position_in_trajectory'])




df_sorted['trend_label'] = None

trend_labels = get_trend_labels(df_sorted)


df_sorted['trend_label'] = df_sorted['trajID'].map(dict(trend_labels))


df_sorted.to_csv('./dataset/dataAnaly/disAnaly/trajectory_distances_TKY_split200_test.csv', index=False)


for traj_id, group in df_sorted.groupby('trajID'):
    distance_to_end = group['distance_to_end'].values
    positions = np.arange(len(distance_to_end))
    
   
    model, predicted_distance, mse = fit_polynomial_trend(distance_to_end, degree=2)
    
    
    if 'increasing_then_decreasing' in df_sorted.loc[df_sorted['trajID'] == traj_id, 'trend_label'].values:
        fitted_curve = fit_gaussian_trend(distance_to_end)
        plt.plot(positions, distance_to_end, label=f"Original {traj_id}")
        plt.plot(positions, fitted_curve, label=f"Fitted (Gaussian) {traj_id}")
    else:
        plt.plot(positions, distance_to_end, label=f"Original {traj_id}")
        plt.plot(positions, predicted_distance, label=f"Fitted (Poly) {traj_id}")
    
    plt.title(f"Fitted Curve for Traj {traj_id} (MSE: {mse:.2f})")
    plt.xlabel('POI Position')
    plt.ylabel('Distance to End')
    plt.legend()
    plt.savefig(f"./dataset/dataAnaly/disAnaly/curveFit-TKY/traj_{traj_id}_fitted_curve.png")
    plt.close()
