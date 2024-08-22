// test.js

async function testScrapeSubLinks() {
    const url = 'http://127.0.0.1:5008/scrape_sub_links';
    const testUrl = 'https://www.familysearch.org/de/wiki/Deutsches_Kaiserreich';

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: testUrl }),
    });

    if (response.ok) {
        const jsonResponse = await response.json();
        console.log('Scrape Sub Links Response:', JSON.stringify(jsonResponse, null, 2));
    } else {
        console.error('Error in scrape_sub_links:', response.status, response.statusText);
    }
}

async function testArchive() {
    const url = 'http://127.0.0.1:5008/archive';
    const testUrl = 'https://www.familysearch.org/de/wiki/Deutsches_Kaiserreich';
    const savePath = '/path/to/save';  // Adjust this path as needed

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            urls: [testUrl],
            url: testUrl,
            save_path: savePath,
        }),
    });

    if (response.ok) {
        const jsonResponse = await response.json();
        console.log('Archive Response:', JSON.stringify(jsonResponse, null, 2));
    } else {
        console.error('Error in archive:', response.status, response.statusText);
    }
}

async function runTests() {
    console.log('Starting tests...');
    await testScrapeSubLinks();
    await testArchive();
    console.log('Tests completed.');
}

runTests();
