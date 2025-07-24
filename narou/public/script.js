document.addEventListener('DOMContentLoaded', () => {
    const novelContainer = document.getElementById('novel-container');
    const titleEl = document.getElementById('title');
    const authorEl = document.getElementById('author');
    const contentEl = document.getElementById('content');

    const savedNovel = localStorage.getItem('novelData');

    if (savedNovel) {
        const novelData = JSON.parse(savedNovel);
        displayNovel(novelData);
    } else {
        fetchNovel();
    }

    function fetchNovel() {
        fetch('/novel')
            .then(response => response.json())
            .then(data => {
                localStorage.setItem('novelData', JSON.stringify(data));
                displayNovel(data);
            })
            .catch(error => {
                console.error('Error fetching novel:', error);
                contentEl.textContent = '小説の読み込みに失敗しました。インターネット接続を確認して、ページを再読み込みしてください。';
            });
    }

    function displayNovel(data) {
        titleEl.textContent = data.title;
        authorEl.textContent = data.author;
        contentEl.textContent = data.content;
    }
});
