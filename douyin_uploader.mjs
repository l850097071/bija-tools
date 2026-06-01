#!/usr/bin/env node
/**
 * Bija抖音上传桥接脚本
 * 用法: node douyin_uploader.mjs <action> [args...]
 *   node douyin_uploader.mjs status
 *   node douyin_uploader.mjs login
 *   node douyin_uploader.mjs upload <video_path> <title> <tags_json>
 */
import { pathToFileURL } from 'url';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Resolve the douyin-mcp-server module
const npmRoot = 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/douyin-mcp-server';
const uploaderPath = path.join(npmRoot, 'mcp-server/dist/douyin-uploader.js');
const uploaderUrl = pathToFileURL(uploaderPath).href;

const { DouyinUploader } = await import(uploaderUrl);
const uploader = new DouyinUploader();

const action = process.argv[2];

async function doStatus() {
    const check = await uploader.checkLogin(false);
    console.log(JSON.stringify(check));
}

async function doLogin() {
    console.log('Checking login status...');
    const check = await uploader.checkLogin(false);
    if (check.isValid) {
        console.log(JSON.stringify({success: true, user: check.user, message: 'Already logged in'}));
        return;
    }
    console.log('Opening browser for QR code login...');
    console.log('Scan the QR code with抖音 App within 3 minutes.');
    const result = await uploader.login(false, 180000);
    console.log(JSON.stringify(result));
}

async function doUpload(videoPath, title, tagsJson) {
    const check = await uploader.checkLogin(false);
    if (!check.isValid) {
        console.log(JSON.stringify({success: false, error: 'Not logged in'}));
        return;
    }
    console.log(`Logged in as: ${check.user}`);

    let tags = ['科普', '知识'];
    if (tagsJson && tagsJson !== '-') {
        try {
            tags = JSON.parse(tagsJson);
        } catch(e) {}
    }

    const result = await uploader.uploadVideo({
        videoPath: videoPath,
        title: title || `DFT避坑 ${new Date().toLocaleDateString()}`,
        description: '',
        tags: tags,
        headless: true,
        autoPublish: true
    });
    console.log(JSON.stringify(result));
}

if (action === 'status') {
    await doStatus();
} else if (action === 'login') {
    await doLogin();
} else if (action === 'upload') {
    const videoPath = process.argv[3];
    const title = process.argv[4] || '';
    const tagsJson = process.argv[5] || '["科普","知识"]';
    if (!videoPath) {
        console.log(JSON.stringify({success: false, error: 'No video path provided'}));
        process.exit(1);
    }
    await doUpload(videoPath, title, tagsJson);
} else {
    console.log('Usage: node douyin_uploader.mjs <status|login|upload> [args]');
}
