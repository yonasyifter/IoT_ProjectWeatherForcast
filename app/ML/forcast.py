import kagglehub
import pandas as pd
import os
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Download latest version
path = kagglehub.dataset_download("zeeshier/weather-forecast-dataset")

print("Path to dataset files:", path)

# List all files in the downloaded directory
files_in_dataset = os.listdir(path)

# Filter for CSV files
csv_files = [f for f in files_in_dataset if f.endswith('.csv')]

if not csv_files:
    raise FileNotFoundError(f"No CSV files found in the dataset directory: {path}")

# Assuming the first CSV file found is the correct one for simplicity.
# If there are multiple CSVs and specific one is needed, further logic may be required.
first_csv_file = csv_files[0]
full_csv_path = os.path.join(path, first_csv_file)

df = pd.read_csv(full_csv_path)

print(f"Successfully loaded '{first_csv_file}'.")

df = df.dropna()

X = df[[
    "Temperature",
    "Humidity",
    "Wind_Speed",
    "Cloud_Cover",
    "Pressure"
]]
Y = df["Rain"]

# Normalize
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X_scaled, Y, test_size=0.2, shuffle=False)

# Small NN (TFLite optimized)
model = tf.keras.Sequential([
    tf.keras.layers.Dense(16, activation="relu", input_shape=(X_train.shape[1],)),
    tf.keras.layers.Dense(8, activation="relu"),
    tf.keras.layers.Dense(1)
])

y_train = y_train.map({'no rain': 0, 'rain': 1})
y_test = y_test.map({'no rain': 0, 'rain': 1})

# Small NN (TFLite optimized)
model = tf.keras.Sequential([
    tf.keras.layers.Dense(16, activation="relu", input_shape=(X_train.shape[1],)),
    tf.keras.layers.Dense(8, activation="relu"),
    tf.keras.layers.Dense(1)
])

model.compile(
    optimizer="adam",
    loss="mse",
    metrics=["mae"]
)

model.fit(
    X_train, y_train,
    epochs=30,
    batch_size=8,
    validation_data=(X_test, y_test),
    verbose=1
)

from sklearn.metrics import accuracy_score

# Make predictions with the Neural Network model on the test set
y_pred_nn_raw = model.predict(X_test)

# Convert raw predictions to binary (0 or 1) using a 0.5 threshold
y_pred_nn = (y_pred_nn_raw >= 0.5).astype(int)

# Calculate accuracy for the Neural Network
accuracy_nn = accuracy_score(y_test, y_pred_nn)

print(f"Neural Network Model Accuracy on Test Set: {accuracy_nn:.4f}")
print(f"RandomForest Model Accuracy on Test Set: {accuracy_rf:.4f}")

print("\nComparison:")
if accuracy_nn > accuracy_rf:
    print(f"The Neural Network model has a higher accuracy of {accuracy_nn:.4f} compared to RandomForest's {accuracy_rf:.4f}.")
elif accuracy_rf > accuracy_nn:
    print(f"The RandomForest model has a higher accuracy of {accuracy_rf:.4f} compared to Neural Network's {accuracy_nn:.4f}.")
else:
    print(f"Both models have the same accuracy of {accuracy_nn:.4f}.")