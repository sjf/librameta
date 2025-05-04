const PLACEHOLDER_COVER = "/static/cover.png";
const EXTS = ['epub','mobi','djvu','pdf'];
let currentFocus;

print('js');

document.addEventListener('DOMContentLoaded', function() {
  addListeners();
  fillSearchParamsFromUrl();
  hideElement('cant-submit');
});

function addListeners() {
  const closeButtons = document.getElementsByClassName('close-flash');
  for (const closeButton of closeButtons) {
    closeButton.addEventListener('click', onCloseFlashClicked);
  };

  // Search listeners.
  document.getElementById('advanced-search-button').addEventListener('click', onAdvancedSearchButtonClicked);
  document.getElementById('show-advanced-search').addEventListener('click', onShowAdvancedSearchClicked);
  document.getElementById('show-basic-search').addEventListener('click', onShowBasicSearchClicked);
  document.getElementById('back-to-query').addEventListener('click', onBackToQueryClicked);
  window.addEventListener('popstate', onPopState);

  const elems = document.getElementsByClassName('edit-query');
  for (const elem of elems) {
    elem.addEventListener('click', onEditQueryClicked);
  };

  // Search box clear buttons.
  document.querySelectorAll('.clearbutton').forEach(button => {
    button.addEventListener('click', function() {
       // Clear all input under the same parent element.
      this.parentElement.querySelectorAll('input').forEach(input => {
        input.value = '';
        input.checked = false;
      });
    });
  });

  const rangeButton = document.getElementById('range-button');
  rangeButton.addEventListener('click', function() {
    if (this.checked) {
      document.getElementById('year1-label').textContent = 'Start:';
      document.getElementById('year1').name = 'start_year';
      showElement('end-year');
      // document.getElementById('end-year').classList.remove('hidden');
    } else {
      document.getElementById('year1-label').textContent = '';
      document.getElementById('year1').name = 'year';
      document.getElementById('end_year').value = '';
      hideElement('end-year');
    }
  });

  // Language autocomplete
  langInput = document.getElementById('lang');
  langInput.addEventListener('input', onLangInput);
  langInput.addEventListener('keydown', onLangInputKeyDown);
  langInput.addEventListener('onblur', closeDropdown)
  document.addEventListener('click', closeDropdown);

  // Results page
  setupCoverListeners();

  const links = document.getElementsByClassName('download');
  for (const link of links) {
    link.addEventListener('click', onDownloadLinkClicked);
    link.addEventListener('auxclick', onDownloadLinkClicked);
  };
}

function onDownloadLinkClicked(event) {
  const urlPath = window.location.href.split(window.location.origin)[1];

  const a = event.target;
  const title = a.closest('.book').querySelector('.title').textContent.trim();
  const authors = a.closest('.book').querySelector('.authors').textContent.trim();

  log('download', {
    'urlpath': urlPath,
    'id':  a.dataset.id,
    'button': a.textContent,
    'position': a.dataset.position,
    'title': title,
    'authors': authors
  });
}

function onCloseFlashClicked(event) {
  hideElement(event.target.closest('.flash'));
}

function onAdvancedSearchButtonClicked(){
  hideElement('cant-submit');
  var isFilled = false;
  for (let id of ['title', 'author', 'series']) {
    const input = document.getElementById(id);
    if (input.value != '') {
      isFilled = true;
      break;
    }
  }
  if (!isFilled) {
    event.preventDefault();
    flash("cant-submit");
  }
}

function showAdvancedSearch() {
  hideElement('cant-submit');
  showElement('advanced-search');
  hideElement('basic-search');
}

function showBasicSearch() {
  hideElement('cant-submit');
  hideElement('advanced-search');
  showElement('basic-search');
}

function onShowAdvancedSearchClicked() {
  event.preventDefault();
  showAdvancedSearch();
  history.pushState({'search':'advanced'}, '', '/adv');
  // print(history.state);
}

function onShowBasicSearchClicked() {
  event.preventDefault();
  showBasicSearch();
  history.pushState({'search':'basic'}, '', '/');
  // print(history.state);
}

function onEditQueryClicked() {
  hideElement('advanced-query');
  showAdvancedSearch();

  showElement('show-basic-search');
  showElement('back-to-query');
  if (this.dataset['target']) {
    document.getElementById(this.dataset['target']).focus();
  }
}

function onBackToQueryClicked() {
  event.preventDefault();
  hideElement('cant-submit');
  hideElement('advanced-search');
  showElement('advanced-query')

  showElement('show-basic-search');
  hideElement('back-to-query');
}

function onPopState(e) {
  // print(window.location.href);
  // print('history')
  // print('pop state');
  // print(history.state);
  // print('state')
  // print(e.state)
  if (!e.state) {
    path = window.location.pathname;
    if (path == '/' || path == '/search') {
      showBasicSearch();
    } else if (path == '/adv' || path == '/search-adv') {
      showAdvancedSearch();
    } else {
      location.reload();
    }
  } else if (e.state.search == 'basic') {
    showBasicSearch();
  } else if (e.state.search == 'advanced') {
    showAdvancedSearch();
  }
}

function setupCoverListeners() {
  // Images that missing from the OL covers API show as 1x1px images.
  // Replace these with the cover placeholder if they load.
  const imgs = document.getElementsByClassName('cover');
  for (const img of imgs) {
    if (img.src.includes(PLACEHOLDER_COVER)) {
      // skip already placeholder.
      continue;
    }
    if (img.complete) {
      // already loaded.
      checkCover(img);
    } else {
      // add listener.
      img.addEventListener('load', (e) => checkCover(e.target));
      img.addEventListener('error', onCoverFail);
    }
  }
}

function checkCover(img) {
  if (img.src.includes(PLACEHOLDER_COVER)) {
    return;
  }
  title = img.parentElement.getElementsByClassName('title')[0].innerText;
  authors = img.parentElement.getElementsByClassName('authors')[0].innerText

  const coverisbn = img.dataset.coverisbn;
  const attempt = parseInt(img.dataset.attempt, 10);

  // check width of actual image, not CSS size.
  if (img.naturalWidth > 1 && img.naturalHeight > 1) {
    print(`${title} ${authors} Found cover for ${coverisbn} on attempt ${attempt}.`);
    // cover image loaded.
    // img.onclick = zoomImage;
    return;
  }

  // the cover image did not load.
  const isbns = img.dataset.isbns.split(',')
  const remaining = isbns.filter(item => item !== coverisbn);

  if (remaining.length != 0) {
    print(`${title} ${authors} No cover for ${coverisbn}. Trying isbn ${remaining[0]}...`);
    img.src = `https://covers.openlibrary.org/b/isbn/${remaining[0]}-M.jpg`;
    img.dataset.coverisbn = remaining[0];
    img.dataset.isbns = remaining.join(',');
    img.dataset.attempt = attempt + 1;
  } else {
    print(`${title} ${authors} No cover for ${coverisbn}.`);
    // Use the placehold cover.
    img.src = PLACEHOLDER_COVER;
    img.dataset.coverisbn = '';
    img.dataset.isbns = '';
    img.classList.remove('cover-image');
  }
}

function onCoverFail(e) {
  const img = e.target;
  if (img.src.includes(PLACEHOLDER_COVER)) {
    return;
  }
  const title = img.parentElement.getElementsByClassName('title')[0].innerText;
  const authors = img.parentElement.getElementsByClassName('authors')[0].innerText
  print(`${title} ${authors} Cover did not load.`);

  img.src = PLACEHOLDER_COVER;
  return true;
}

function onLangInput() {
  let val = this.value;
  document.getElementById('dropdown-content').innerHTML = '';
  if (!val) {
    return false;
  }
  currentFocus = -1;

  const list = document.getElementById('dropdown-content');
  var match = '';
  for (const [names, displayName, langCode] of languages) {
    if (val.toLowerCase() == name) {
      match = langCode;
    }
    for (name of names) {
      if (val.toLowerCase() == name.substr(0, val.length)) {
        // Matches language prefix.
        const listItem = document.createElement('li');
        const a = document.createElement('a');
        a.innerText = displayName;
        listItem.addEventListener('click', function() {
          langInput.value = displayName;
          document.getElementById('lang-code').value = langCode;
          closeDropdown();
        });
        listItem.appendChild(a)
        list.appendChild(listItem);
        break;
      }
    }
  }
  document.getElementById('lang-code').value = match;
};

function onLangInputKeyDown(e) {
  let items = document.querySelectorAll('.dropdown-content li');
  if (!items) {
    return
  }
  if (e.keyCode == 40) { // Down arrow
    currentFocus++;
    updateSelected(items);
  } else if (e.keyCode == 38) { // Up arrow
    currentFocus--;
    updateSelected(items);
  } else if (e.keyCode == 13) { // Enter
    e.preventDefault();
    if (currentFocus > -1) {
      items[currentFocus].click();
    }
  }
}

function updateSelected(items) {
  if (!items) return false;
  if (currentFocus >= items.length) currentFocus = 0;
  if (currentFocus < 0) currentFocus = items.length - 1;

  for (let i = 0; i < items.length; i++) {
    items[i].classList.remove('dropdown-selected');
  }
  items[currentFocus].classList.add('dropdown-selected');
}

function closeDropdown() {
  document.getElementById('dropdown-content').innerHTML = '';
  if (!document.getElementById('lang-code').value) {
    langInput.value = '';
  }
}

function fillSearchParamsFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const names = ['search','author','title','series','lang'];
  for (name of names) {
    if (isset(params, name)) {
      document.getElementById(name).value = params.get(name);
    }
  }
  if (isset(params, 'year')) {
    document.getElementById('year1').value = params.get('year');
  }
  // Year range
  if (isset(params,'start_year') || isset(params,'end_year')) {
    if (isset(params,'start_year')) {
      document.getElementById('year1').value = params.get('start_year');
    }
    if (isset(params,'end_year')) {
      document.getElementById('end_year').value = params.get('end_year');
    }
    document.getElementById('range-button').click();
  }
  // Set something for the basic search.
  // if (!params.has('search')) {
  //   // // Just do this for now.
  //   // search = [params.get('author'), params.get('title'), params.get('series')].join(' ');
  //   // if (search) {
  //   //   document.getElementById('search').value = search;
  //   // }
  // }
  if (isset(params, 'search') && !isset(params,'title')) {
    // Populate the title with the search query, so switching between forms
    // means less typing.
    document.getElementById('title').value = params.get('search');    
  }
  if (isset(params, 'lang')) {
    const code = params.get('lang');
    if (code in language_names_by_code) {
      document.getElementById('lang-code').value = code;
      document.getElementById('lang').value = language_names_by_code[code];
    }
  }
  for (ext of params.getAll('ext')) {
    const cb = document.getElementById('filter-' + ext);
    if (cb) {
      cb.checked = true;
    }
  }
}

function isset(params, key) {
  return params.has(key) && params.get(key) != '';
}

function flash(id, message) {
  const flash = document.getElementById(id);
  if (message) {
    flash.firstChild.nodeValue = message;
  }
  showElement(flash);
}

function hideElement(obj) {
  _maybeGetElement(obj).classList.add('display-none');
}
function showElement(obj) {
  _maybeGetElement(obj).classList.remove('display-none');
}
function _maybeGetElement(obj) {
  if (typeof obj === 'string') {
    return document.getElementById(obj)
  }
  if (obj instanceof Element) {
    return obj;
  }
  throw new Error('Unhandled type');
}
function log(name, data) {
 navigator.sendBeacon('/log', JSON.stringify({'name': name, 'data': data}));
}

function print(o){
  // console.log(window.DEBUG);
  // if (typeof window.DEBUG === 'undefined') {
  //   return;
  // }
  if (!DEBUG) {
    return;
  }
  console.log(JSON.stringify(o));
}
