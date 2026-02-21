class EyeController {
  constructor(elements = {}, eyeSize = "33.33vmin") {
    this._eyeSize = eyeSize;
    this._blinkTimeoutID = null;

    this.setElements(elements);
  }

  get leftEye() {
    return this._leftEye;
  }
  get rightEye() {
    return this._rightEye;
  }

  setElements({
    leftEye,
    rightEye,
    upperLeftEyelid,
    upperRightEyelid,
    lowerLeftEyelid,
    lowerRightEyelid,
  } = {}) {
    this._leftEye = leftEye;
    this._rightEye = rightEye;
    this._upperLeftEyelid = upperLeftEyelid;
    this._upperRightEyelid = upperRightEyelid;
    this._lowerLeftEyelid = lowerLeftEyelid;
    this._lowerRightEyelid = lowerRightEyelid;
    return this;
  }

  async blink({ duration = 150 } = {}) {
    console.log("Blinking...");

    // Send API request
    try {
      await fetch("/api/blink", { method: "POST" });
    } catch (error) {
      console.error("API Error:", error);
    }

    if (!this._leftEye) {
      console.warn("Eye elements are not set.");
      return;
    }

    [this._leftEye, this._rightEye].forEach((eye) => {
      eye.animate(
        [
          { transform: "rotateX(0deg)" },
          { transform: "rotateX(90deg)" },
          { transform: "rotateX(0deg)" },
        ],
        {
          duration,
          iterations: 1,
        }
      );
    });
  }

  async express({ type = "", duration = 5000, enterDuration = 75, exitDuration = 75 }) {
    console.log(`Expressing: ${type}`);

    // Send API request
    try {
      await fetch("/api/express", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type }),
      });
    } catch (error) {
      console.error("API Error:", error);
    }

    if (!this._leftEye) {
      console.warn("Eye elements are not set.");
      return;
    }

    // Cancel any running eyelid animations before starting new ones
    if (this._activeAnimations) {
      this._activeAnimations.forEach(anim => anim.cancel());
    }
    this._activeAnimations = [];

    const options = { duration: duration, fill: "none" };

    const addAnim = (el, keyframes) => {
      const anim = el.animate(keyframes, options);
      this._activeAnimations.push(anim);
    };

    switch (type) {
      case "happy":
        addAnim(this._lowerLeftEyelid, this._createKeyframes("-2/3", "30deg", enterDuration, exitDuration));
        addAnim(this._lowerRightEyelid, this._createKeyframes("-2/3", "-30deg", enterDuration, exitDuration));
        break;
      case "sad":
        addAnim(this._upperLeftEyelid, this._createKeyframes("1/3", "-20deg", enterDuration, exitDuration));
        addAnim(this._upperRightEyelid, this._createKeyframes("1/3", "20deg", enterDuration, exitDuration));
        break;
      case "angry":
        addAnim(this._upperLeftEyelid, this._createKeyframes("1/4", "30deg", enterDuration, exitDuration));
        addAnim(this._upperRightEyelid, this._createKeyframes("1/4", "-30deg", enterDuration, exitDuration));
        break;
      case "focused":
        addAnim(this._upperLeftEyelid, this._createKeyframes("1/3", "0deg", enterDuration, exitDuration));
        addAnim(this._upperRightEyelid, this._createKeyframes("1/3", "0deg", enterDuration, exitDuration));
        addAnim(this._lowerLeftEyelid, this._createKeyframes("-1/3", "0deg", enterDuration, exitDuration));
        addAnim(this._lowerRightEyelid, this._createKeyframes("-1/3", "0deg", enterDuration, exitDuration));
        break;
      case "confused":
        addAnim(this._upperRightEyelid, this._createKeyframes("1/3", "-10deg", enterDuration, exitDuration));
        break;
      default:
        console.warn(`Invalid expression type: ${type}`);
    }
  }

  _createKeyframes(tgtTranYVal, tgtRotVal, enterDuration, exitDuration) {
    return [
      { transform: "translateY(0px) rotate(0deg)", offset: 0.0 },
      { transform: `translateY(calc(${this._eyeSize} * ${tgtTranYVal})) rotate(${tgtRotVal})`, offset: enterDuration / 1000 },
      { transform: `translateY(calc(${this._eyeSize} * ${tgtTranYVal})) rotate(${tgtRotVal})`, offset: 1 - exitDuration / 1000 },
      { transform: "translateY(0px) rotate(0deg)", offset: 1.0 },
    ];
  }

  startBlinking({ maxInterval = 5000 } = {}) {
    if (this._blinkTimeoutID) {
      console.warn(`Already blinking with timeoutID=${this._blinkTimeoutID}; return;`);
      return;
    }

    const blinkRandomly = (timeout) => {
      this._blinkTimeoutID = setTimeout(() => {
        this.blink();
        blinkRandomly(Math.random() * maxInterval);
      }, timeout);
    };
    blinkRandomly(Math.random() * maxInterval);
  }

  stopBlinking() {
    clearTimeout(this._blinkTimeoutID);
    this._blinkTimeoutID = null;
  }
}

const eyes = new EyeController({
  leftEye: document.querySelector(".left.eye"),
  rightEye: document.querySelector(".right.eye"),
  upperLeftEyelid: document.querySelector(".left .eyelid.upper"),
  upperRightEyelid: document.querySelector(".right .eyelid.upper"),
  lowerLeftEyelid: document.querySelector(".left .eyelid.lower"),
  lowerRightEyelid: document.querySelector(".right .eyelid.lower"),
});

// Auto-start blinking for a lifelike appearance
eyes.startBlinking();

// --- WebSocket connection for real-time emotion updates ---
let currentEmotion = null;
let socket;

function connectWebSocket() {
  socket = new WebSocket(`ws://${window.location.host}/ws`);

  socket.onopen = () => {
    console.log("✅ Connected to emotion WebSocket");
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "emotion_update" && data.emotion !== currentEmotion) {
      console.log("🎭 Emotion update:", data.emotion);
      currentEmotion = data.emotion;
      eyes.express({ type: data.emotion, duration: 8000 });
    }
  };

  socket.onclose = () => {
    console.log("❌ WebSocket disconnected, reconnecting in 3s...");
    setTimeout(connectWebSocket, 3000);
  };

  socket.onerror = (err) => {
    console.error("WebSocket error:", err);
  };
}

connectWebSocket();
