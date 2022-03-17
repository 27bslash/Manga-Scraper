const inContent1 = () => {
  if (!newEntry()) {
    return;
  }
  //   mangaTitle();

  const el = document.createElement("div");
  el.classList.add("manga-scraper-overlay");
  el.style.cssText =
    "position:fixed; top:0; left:0; right:0; background:white;color:black";
  el.textContent = document.title;
  document.body.appendChild(el);
  console.log(extractTitle(document.title));
};
const cleanUp = () => {
  document.querySelectorAll(".manga-scraper-overlay").remove();
};
const newEntry = () => {
  return true;
};
const extractTitle = (title) => {
  let chapterNum = "",
    seriesTitle = "",
    scanSite = "";
  const getChapterNum = (title) => {
    console.log("call");
    const chapterRegex = /(?<=episode\s|chapter\s|#)\d+\.?\d*/im;
    // get number after chapter then remove leading zeros
    chapterNum = title.match(chapterRegex);
    seriesTitle = seriesTitle
      // remove chapter numbers
      .replace(chapterRegex, "")
      .replace(/chapter|episode/gi, "")
      // remove special characters
      .replace(/:|\-|\–|\||\[#\]/gm, "")
      .trim();
    if (chapterNum) {
      chapterNum = chapterNum[0].replace(/^0+/, "");
    }
  };

  const scans = (title) => {
    const scanRegex = /\w+\s?\w+$/gim;
    seriesTitle = title.replace(scanRegex, "");
    if (title.toLowerCase().includes("episode")) {
      // webttons edge case
      scanSite = "webtoons";
    } else {
      scanSite = title.match(scanRegex)[0];
    }
  };
  scans(title);
  getChapterNum(title);
  return { title: seriesTitle, chapter: +chapterNum, scanSite: scanSite };
};
// chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
//   console.log(message);
//   return true;
// });
inContent1();
