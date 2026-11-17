"""Camera + Google ML Kit pose detection through pyjnius (Android only).
Needs the app built with the 'camera' option (adds the ML Kit library). Everything is imported lazily so the
app still starts when the library is missing."""
import time

LANDMARKS = {
    "l_shoulder": "LEFT_SHOULDER", "r_shoulder": "RIGHT_SHOULDER", "l_elbow": "LEFT_ELBOW", "r_elbow": "RIGHT_ELBOW",
    "l_wrist": "LEFT_WRIST", "r_wrist": "RIGHT_WRIST", "l_hip": "LEFT_HIP", "r_hip": "RIGHT_HIP",
    "l_knee": "LEFT_KNEE", "r_knee": "RIGHT_KNEE", "l_ankle": "LEFT_ANKLE", "r_ankle": "RIGHT_ANKLE",
}


def available():
    try:
        from jnius import autoclass
        autoclass("com.google.mlkit.vision.pose.PoseDetection")
        return True
    except Exception:
        return False


def diagnose():
    """Plain-English lines for ADMIN > CAMERA CHECK."""
    lines = ["camera_pose.py: found"]
    try:
        from jnius import autoclass
    except Exception:
        return lines + ["Android bridge: not available (are you on a computer?)"]
    lines.append("ML Kit pose library: " + ("found" if available() else "MISSING - build the APK with the camera option"))
    try:
        lines.append("Cameras on this phone: %d" % autoclass("android.hardware.Camera").getNumberOfCameras())
    except Exception as e:
        lines.append("Camera access error: %s" % e)
    return lines


def _listener_classes():
    from jnius import PythonJavaClass, java_method

    class OnSuccess(PythonJavaClass):
        __javainterfaces__ = ["com/google/android/gms/tasks/OnSuccessListener"]
        __javacontext__ = "app"

        def __init__(self, cb):
            super().__init__()
            self.cb = cb

        @java_method("(Ljava/lang/Object;)V")
        def onSuccess(self, result):
            self.cb(result)

    class OnFailure(PythonJavaClass):
        __javainterfaces__ = ["com/google/android/gms/tasks/OnFailureListener"]
        __javacontext__ = "app"

        def __init__(self, cb):
            super().__init__()
            self.cb = cb

        @java_method("(Ljava/lang/Exception;)V")
        def onFailure(self, error):
            self.cb(error)

    class Preview(PythonJavaClass):
        __javainterfaces__ = ["android/hardware/Camera$PreviewCallback"]
        __javacontext__ = "app"

        def __init__(self, cb):
            super().__init__()
            self.cb = cb

        @java_method("([BLandroid/hardware/Camera;)V")
        def onPreviewFrame(self, data, camera):
            self.cb(data)

    return OnSuccess, OnFailure, Preview


class PoseCamera:
    """Opens the camera (no preview on screen) and calls on_landmarks({name: (x, y, likelihood)}) ~10 times a second."""

    def __init__(self, on_landmarks, front=True):
        self.on_landmarks = on_landmarks
        self.front = front
        self.cam = None
        self.detector = None
        self.busy = False
        self.last = 0.0
        self.frames = 0
        self.poses = 0
        self.error = ""

    def start(self):
        """Raises RuntimeError('<step>: <error>') so the screen can say which step failed."""
        step = "loading Java classes"
        try:
            from jnius import autoclass, cast
            Camera = autoclass("android.hardware.Camera")
            CameraInfo = autoclass("android.hardware.Camera$CameraInfo")
            step = "finding the camera"
            info = CameraInfo()
            want = CameraInfo.CAMERA_FACING_FRONT if self.front else CameraInfo.CAMERA_FACING_BACK
            cam_id = 0
            for i in range(Camera.getNumberOfCameras()):
                Camera.getCameraInfo(i, info)
                if info.facing == want:
                    cam_id = i
                    break
            Camera.getCameraInfo(cam_id, info)
            self.rotation = info.orientation  # the app is portrait only
            step = "opening the camera"
            self.cam = Camera.open(cam_id)
            step = "setting up the camera"
            self._setup(autoclass, cast)
            step = "starting the preview"
            self.cam.startPreview()
        except Exception as e:
            self.stop()
            raise RuntimeError("%s: %s" % (step, e))

    def _setup(self, autoclass, cast):
        params = self.cam.getParameters()
        sizes = params.getSupportedPreviewSizes()
        best, best_diff = None, None
        for i in range(sizes.size()):
            s = cast("android.hardware.Camera$Size", sizes.get(i))
            diff = abs(s.width * s.height - 640 * 480)
            if best is None or diff < best_diff:
                best, best_diff = s, diff
        self.w, self.h = best.width, best.height
        params.setPreviewSize(self.w, self.h)
        params.setPreviewFormat(17)  # NV21
        self.cam.setParameters(params)

        OnSuccess, OnFailure, Preview = _listener_classes()
        self._ok, self._fail, self._preview = OnSuccess(self._on_pose), OnFailure(self._on_error), Preview(self._on_frame)
        opts_cls = autoclass("com.google.mlkit.vision.pose.defaults.PoseDetectorOptions")
        opts = autoclass("com.google.mlkit.vision.pose.defaults.PoseDetectorOptions$Builder")().setDetectorMode(
            opts_cls.STREAM_MODE).build()
        self.detector = autoclass("com.google.mlkit.vision.pose.PoseDetection").getClient(opts)
        self._texture = autoclass("android.graphics.SurfaceTexture")(10)
        self.cam.setPreviewTexture(self._texture)
        self.cam.setPreviewCallback(self._preview)

    def _on_frame(self, data):
        now = time.time()
        if self.busy or now - self.last < 0.1:
            return
        self.busy, self.last = True, now
        self.frames += 1
        try:
            from jnius import autoclass
            image = autoclass("com.google.mlkit.vision.common.InputImage").fromByteArray(data, self.w, self.h, self.rotation, 17)
            self.detector.process(image).addOnSuccessListener(self._ok).addOnFailureListener(self._fail)
        except Exception as e:
            self.busy, self.error = False, str(e)

    def _on_pose(self, result):
        try:
            from jnius import autoclass, cast
            pose = cast("com.google.mlkit.vision.pose.Pose", result)
            consts = autoclass("com.google.mlkit.vision.pose.PoseLandmark")
            found = {}
            for name, const in LANDMARKS.items():
                lm = pose.getPoseLandmark(getattr(consts, const))
                if lm is not None:
                    p = lm.getPosition()
                    found[name] = (p.x, p.y, lm.getInFrameLikelihood())
            if found:
                self.poses += 1
            self.on_landmarks(found)
        except Exception as e:
            self.error = str(e)
        finally:
            self.busy = False

    def _on_error(self, error):
        self.error = str(error)
        self.busy = False

    def stop(self):
        try:
            if self.cam is not None:
                self.cam.setPreviewCallback(None)
                self.cam.stopPreview()
                self.cam.release()
        except Exception:
            pass
        try:
            if self.detector is not None:
                self.detector.close()
        except Exception:
            pass
        self.cam = self.detector = None
