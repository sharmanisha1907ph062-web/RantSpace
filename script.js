// =========================================================
// RantSpace script
// This file makes the buttons work and switches between screens.
// Nothing here sends or saves your rant anywhere.
// The text only lives in the textarea until you leave the page
// or press "End Session".
// =========================================================


// ---------- 1) GRAB THE PIECES OF THE PAGE WE NEED ----------
// document.getElementById("something") finds an element by its id in index.html

const allScreens = document.querySelectorAll(".screen");

const rantInput = document.getElementById("rant-input");
const rantError = document.getElementById("rant-error");

const responseTitle = document.getElementById("response-title");
const responseText = document.getElementById("response-text");


// ---------- 2) THE PLACEHOLDER RESPONSES ----------
// Each option has a title and some text.
// The keys ("listen", "understand", ...) match the data-choice
// values on the buttons in index.html.

const responses = {
  listen: {
    title: "🫂 Just Listen",
    text: "I'm here, and I heard all of it. That sounds like a lot to carry. You don't need to fix anything right now. Take a breath. There's no rush."
  },
  understand: {
    title: "🧠 Help Me Understand",
    text: "This is where RantSpace will help you see what's underneath: what you're feeling, what set it off, and what seems to matter most to you."
  },
  figure: {
    title: "💡 Help Me Figure It Out",
    text: "This is where RantSpace will help you look at your options and pick one small, manageable next step, without pushing you toward anything."
  },
  words: {
    title: "✍️ Put It Into Words",
    text: "This is where RantSpace will help you turn the tangle into something clear: a message you could send, a journal entry, or a single honest sentence."
  }
};


// ---------- 3) A FUNCTION TO SHOW ONE SCREEN ----------
// A function is a saved set of instructions we can reuse.
// showScreen("screen-rant") hides every screen, then shows that one.

function showScreen(screenId) {
  // Hide all screens
  allScreens.forEach(function (screen) {
    screen.classList.remove("active");
  });

  // Show the one we want
  const target = document.getElementById(screenId);
  target.classList.add("active");

  // Scroll to the top and move keyboard focus to the heading
  // (this helps screen reader and keyboard users know the screen changed)
  window.scrollTo(0, 0);
  const heading = target.querySelector("h1, h2");
  heading.focus();
}


// ---------- 4) HOME SCREEN ----------
document.getElementById("start-btn").addEventListener("click", function () {
  showScreen("screen-rant");
});


// ---------- 5) RANT SCREEN ----------
document.getElementById("rant-back-btn").addEventListener("click", function () {
  showScreen("screen-home");
});

document.getElementById("continue-btn").addEventListener("click", function () {
  // .trim() removes spaces, so a box with only spaces counts as empty
  const rantIsEmpty = rantInput.value.trim() === "";

  if (rantIsEmpty) {
    // Show the gentle message and stay on this screen
    rantError.hidden = false;
    rantInput.focus();
  } else {
    rantError.hidden = true;
    showScreen("screen-choose");
  }
});

// Hide the message as soon as the person starts typing
rantInput.addEventListener("input", function () {
  rantError.hidden = true;
});


// ---------- 6) CHOOSE SCREEN ----------
document.getElementById("choose-back-btn").addEventListener("click", function () {
  showScreen("screen-rant");
});

// Find all four option buttons and give each one a click action
const optionButtons = document.querySelectorAll(".option");

optionButtons.forEach(function (button) {
  button.addEventListener("click", function () {
    // Which option was clicked? e.g. "listen"
    const choice = button.dataset.choice;

    // Put the matching title and text on the response screen
    responseTitle.textContent = responses[choice].title;
    responseText.textContent = responses[choice].text;

    showScreen("screen-response");
  });
});


// ---------- 7) RESPONSE SCREEN ----------
document.getElementById("response-back-btn").addEventListener("click", function () {
  showScreen("screen-choose");
});

document.getElementById("end-btn").addEventListener("click", function () {
  // Clear the rant and reset everything, then go Home
  rantInput.value = "";
  rantError.hidden = true;
  responseTitle.textContent = "";
  responseText.textContent = "";

  showScreen("screen-home");
}); 