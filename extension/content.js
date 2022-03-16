const inContent1 = () => {
  if (!newEntry()) {
    return;
  }
//   mangaTitle();
  const el = document.createElement("div");
  el.classList.add("manga-scraper-overlay");
  el.style.cssText = "position:fixed; top:0; left:0; right:0; background:white";
  el.textContent = "tesrt content";
  document.body.appendChild(el);
  console.log("gfjds");
};
const cleanUp = () => {
  document.querySelectorAll(".manga-scraper-overlay").remove();
};
const mangaTitle = () => {
  chrome.tabs.query({ currentWindow: true, active: true }, function (tabs) {
    console.log(tabs[0].url);
    console.log(tabs[0].title);
  });
};
const mangaChapter = () => {};
const newEntry = () => {
  return true;
};

inContent1();
