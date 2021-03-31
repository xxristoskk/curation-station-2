let x = .01;

function setup() {
  var canvas = createCanvas(36, 50);
  canvas.parent('sketch-holder');
  frameRate(60);
}



function draw() {
  if (mouseIsPressed) {
    let mill = millis();
    fill('red');
    circle(mouseX, mouseY, x*mill);
  }
}
