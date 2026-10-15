import sys
import os
import shutil
import subprocess
from wasteDetection.pipeline.training_pipeline import TrainPipeline
from wasteDetection.utils.main_utils import decodeImage, encodeImageIntoBase64
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS, cross_origin
from wasteDetection.constant.application import APP_HOST, APP_PORT


app = Flask(__name__)
CORS(app)


class ClientApp:
    def __init__(self):
        self.filename = "inputImage.jpg"


clApp = ClientApp()


def get_weights_path() -> str:
    """Find the best available model weights."""
    for candidate in ["my_model.pt", "best.pt", "yolov5s.pt"]:
        if os.path.exists(os.path.join("yolov5", candidate)):
            return candidate
    return "yolov5s.pt"


@app.route("/train")
def trainRoute():
    obj = TrainPipeline()
    obj.run_pipeline()
    return "Training Successfull!!"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/predict", methods=['POST', 'GET'])
@cross_origin()
def predictRoute():
    try:
        image = request.json['image']
        decodeImage(image, clApp.filename)

        weights = get_weights_path()
        runs_dir = os.path.join("yolov5", "runs")
        shutil.rmtree(runs_dir, ignore_errors=True)

        cmd = [
            sys.executable, "detect.py",
            "--weights", weights,
            "--img", "416",
            "--conf", "0.5",
            "--source", "../data/inputImage.jpg",
            "--exist-ok"
        ]
        subprocess.run(cmd, cwd="yolov5", check=True)

        output_image_path = os.path.join("yolov5", "runs", "detect", "exp", "inputImage.jpg")
        opencodedbase64 = encodeImageIntoBase64(output_image_path)
        result = {"image": opencodedbase64.decode('utf-8')}
        shutil.rmtree(runs_dir, ignore_errors=True)

    except ValueError as val:
        print(val)
        return Response("Value not found inside json data")
    except KeyError:
        return Response("Key value error incorrect key passed")
    except Exception as e:
        print(e)
        result = "Invalid input"

    return jsonify(result)


@app.route("/live", methods=['GET'])
@cross_origin()
def predictLive():
    try:
        weights = get_weights_path()
        runs_dir = os.path.join("yolov5", "runs")
        shutil.rmtree(runs_dir, ignore_errors=True)

        cmd = [
            sys.executable, "detect.py",
            "--weights", weights,
            "--img", "416",
            "--conf", "0.5",
            "--source", "0"
        ]
        subprocess.run(cmd, cwd="yolov5")
        shutil.rmtree(runs_dir, ignore_errors=True)
        return "Camera starting!!"

    except ValueError as val:
        print(val)
        return Response("Value not found inside json data")
    except Exception as e:
        print(e)
        return Response(f"Error starting live camera: {e}")


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT)

