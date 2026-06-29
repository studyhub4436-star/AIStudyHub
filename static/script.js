// =========================
// Typing Animation
// =========================

const textArray = [
  "Upload Notes & Study Materials",
  "Search Smartly with NLP",
  "Get AI Recommendations",
  "Download Trending PDFs",
];

let textIndex = 0;
let charIndex = 0;

const typingElement = document.querySelector(".hero p");

function typeText() {
  if (charIndex < textArray[textIndex].length) {
    typingElement.textContent += textArray[textIndex].charAt(charIndex);

    charIndex++;

    setTimeout(typeText, 80);
  } else {
    setTimeout(eraseText, 1500);
  }
}

function eraseText() {
  if (charIndex > 0) {
    typingElement.textContent = textArray[textIndex].substring(
      0,
      charIndex - 1,
    );

    charIndex--;

    setTimeout(eraseText, 40);
  } else {
    textIndex++;

    if (textIndex >= textArray.length) {
      textIndex = 0;
    }

    setTimeout(typeText, 500);
  }
}

window.onload = () => {
  typingElement.textContent = "";

  typeText();
};

// =========================
// Particle Background
// =========================

const canvas = document.createElement("canvas");

document.body.appendChild(canvas);

canvas.style.position = "fixed";

canvas.style.top = "0";

canvas.style.left = "0";

canvas.style.width = "100%";

canvas.style.height = "100%";

canvas.style.zIndex = "-2";

canvas.style.pointerEvents = "none";

const ctx = canvas.getContext("2d");

canvas.width = window.innerWidth;

canvas.height = window.innerHeight;

let particles = [];

class Particle {
  constructor() {
    this.x = Math.random() * canvas.width;

    this.y = Math.random() * canvas.height;

    this.radius = Math.random() * 3 + 1;

    this.dx = (Math.random() - 0.5) * 1;

    this.dy = (Math.random() - 0.5) * 1;
  }

  draw() {
    ctx.beginPath();

    ctx.arc(
      this.x,

      this.y,

      this.radius,

      0,

      Math.PI * 2,
    );

    ctx.fillStyle = "rgba(0,255,255,0.7)";

    ctx.fill();
  }

  update() {
    this.x += this.dx;

    this.y += this.dy;

    if (this.x < 0 || this.x > canvas.width) {
      this.dx *= -1;
    }

    if (this.y < 0 || this.y > canvas.height) {
      this.dy *= -1;
    }

    this.draw();
  }
}

function initParticles() {
  particles = [];

  for (let i = 0; i < 100; i++) {
    particles.push(new Particle());
  }
}

function connectParticles() {
  for (let a = 0; a < particles.length; a++) {
    for (let b = a; b < particles.length; b++) {
      let distance =
        (particles[a].x - particles[b].x) * (particles[a].x - particles[b].x) +
        (particles[a].y - particles[b].y) * (particles[a].y - particles[b].y);

      if (distance < 12000) {
        ctx.beginPath();

        ctx.strokeStyle = "rgba(0,255,255,0.1)";

        ctx.lineWidth = 1;

        ctx.moveTo(
          particles[a].x,

          particles[a].y,
        );

        ctx.lineTo(
          particles[b].x,

          particles[b].y,
        );

        ctx.stroke();
      }
    }
  }
}

function animateParticles() {
  requestAnimationFrame(animateParticles);

  ctx.clearRect(
    0,

    0,

    canvas.width,

    canvas.height,
  );

  particles.forEach((particle) => particle.update());

  connectParticles();
}

initParticles();

animateParticles();

// =========================
// Mouse Glow Effect
// =========================

let mouseX = 0;

let mouseY = 0;

document.addEventListener(
  "mousemove",

  function (e) {
    mouseX = e.clientX;

    mouseY = e.clientY;
  },
);

function mouseGlow() {
  ctx.beginPath();

  ctx.arc(
    mouseX,

    mouseY,

    80,

    0,

    Math.PI * 2,
  );

  ctx.fillStyle = "rgba(0,255,255,0.03)";

  ctx.fill();
}

setInterval(
  mouseGlow,

  30,
);

// =========================
// Resize Canvas
// =========================

window.addEventListener(
  "resize",

  function () {
    canvas.width = window.innerWidth;

    canvas.height = window.innerHeight;

    initParticles();
  },
);
