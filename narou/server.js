const express = require('express');
const axios = require('axios');
const cheerio = require('cheerio');

const app = express();
const port = 3000;

app.use(express.static('public'));

app.get('/novel', async (req, res) => {
    try {
        // 1. 小説の目次ページを取得
        const indexUrl = 'https://ncode.syosetu.com/n4625dt/';
        const indexResponse = await axios.get(indexUrl, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        });
        const indexHtml = indexResponse.data;
        const $ = cheerio.load(indexHtml);

        // 小説のタイトルと作者を取得
        const title = $('#container .novel_title').text();
        const author = $('#container .novel_writername').text();

        // 最初の章のURLを取得
        const firstChapterLink = $('.p-eplist__sublist a').first().attr('href');
        if (!firstChapterLink) {
            throw new Error('最初の章のリンクが見つかりませんでした。');
        }

        const chapterUrl = `https://ncode.syosetu.com${firstChapterLink}`;

        // 2. 最初の章のページを取得
        const chapterResponse = await axios.get(chapterUrl, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': indexUrl // 目次ページをRefererとして設定
            }
        });
        const chapterHtml = chapterResponse.data;
        const $$ = cheerio.load(chapterHtml);

        // 本文を取得
        const content = $$('#novel_honbun').html();
        if (!content) {
            throw new Error('小説の本文が見つかりませんでした。');
        }
        const cleanedContent = content.replace(/<br>/g, '\n').replace(/<p>/g, '').replace(/<\/p>/g, '\n\n');

        res.json({ title, author, content: cleanedContent });
    } catch (error) {
        console.error('Error fetching novel:', error.message);
        res.status(500).json({ error: 'Failed to fetch novel data.' });
    }
});

app.listen(port, () => {
    console.log(`Server listening at http://localhost:${port}`);
});