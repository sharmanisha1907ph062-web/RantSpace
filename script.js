// =========================================================
// RantSpace script
// This file makes the buttons work and switches between screens.
// Rants are sent only to the local RantSpace backend when a response mode is chosen.
// =========================================================


// ---------- 1) GRAB THE PIECES OF THE PAGE WE NEED ----------
// document.getElementById("something") finds an element by its id in index.html

const allScreens = document.querySelectorAll(".screen");

const rantInput = document.getElementById("rant-input");
const rantError = document.getElementById("rant-error");

const responseTitle = document.getElementById("response-title");
const responseText = document.getElementById("response-text");
const responseStatus = document.querySelector(".placeholder-tag");


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

// The existing UI uses "figure" for its third button. The API contract uses
// "figure_out". No API key belongs in browser code.
const apiModes = {
  listen: "listen",
  understand: "understand",
  figure: "figure_out",
  words: "words"
};

const RANT_API_URL = "http://rantspace.onrendor.com/api/rant";
let activeRequestId = 0;


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
  button.addEventListener("click", async function () {
    // Which UI option was clicked? e.g. "listen" or "figure"
    const choice = button.dataset.choice;
    const rant = rantInput.value.trim();

    // Keep the existing empty-rant behavior as a safety check.
    if (!rant) {
      rantError.hidden = false;
      showScreen("screen-rant");
      rantInput.focus();
      return;
    }

    const requestId = ++activeRequestId;

    // Reuse the existing response screen as a loading state.
    responseTitle.textContent = responses[choice].title;
    responseText.textContent = "RantSpace is thinking...";
    responseStatus.textContent = "Getting your response.";
    responseStatus.hidden = false;
    optionButtons.forEach(function (option) {
      option.disabled = true;
    });
    showScreen("screen-response");

    try {
      const backendResponse = await fetch(RANT_API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rant: rant, mode: apiModes[choice] })
      });

      if (!backendResponse.ok) {
        throw new Error("The backend could not create a response.");
      }

      const data = await backendResponse.json();
      if (typeof data.response !== "string") {
        throw new Error("The backend returned an unexpected response.");
      }

      // Avoid replacing a screen after the person navigates away.
      if (requestId !== activeRequestId) return;

      responseText.textContent = data.response;
      responseStatus.hidden = true;
    } catch (error) {
      if (requestId !== activeRequestId) return;

      responseText.textContent =
        "We couldn't reach RantSpace right now. Please make sure the backend is running, then try again.";
      responseStatus.textContent = "Your rant is still here. You can go back and choose again.";
      responseStatus.hidden = false;
    } finally {
      optionButtons.forEach(function (option) {
        option.disabled = false;
      });
    }
  });
});


// ---------- 7) RESPONSE SCREEN ----------
document.getElementById("response-back-btn").addEventListener("click", function () {
  activeRequestId += 1;
  showScreen("screen-choose");
});

document.getElementById("end-btn").addEventListener("click", function () {
  // Clear the rant and reset everything, then go Home
  activeRequestId += 1;
  rantInput.value = "";
  rantError.hidden = true;
  responseTitle.textContent = "";
  responseText.textContent = "";
  responseStatus.hidden = false;

  showScreen("screen-home");
}); 
