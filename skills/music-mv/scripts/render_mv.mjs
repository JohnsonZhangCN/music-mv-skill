#!/usr/bin/env node
// Windows/D-drive entry for the bundled painted-animation renderer.
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, readdirSync } from 'node:fs';
import { resolve, dirname, relative, isAbsolute } from 'node:path';

function parseArgs(values) {
  const args = {};
  for (const value of values) {
    if (!value.startsWith('--')) throw new Error('options must use --name=value');
    const equals = value.indexOf('=');
    const key = value.slice(2, equals < 0 ? undefined : equals);
    args[key] = equals < 0 ? true : value.slice(equals + 1);
  }
  return args;
}
function numberOfRate(value) {
  const [a, b = '1'] = String(value).split('/');
  return Number(a) / Number(b);
}
function verifyMedia(file, task, duration = task.duration) {
  if (!existsSync(file)) throw new Error('rendered file is missing: ' + file);
  const result = spawnSync('ffprobe', ['-v', 'error', '-show_streams', '-show_format', '-of', 'json', file], { encoding: 'utf8' });
  if (result.error || result.status !== 0) throw new Error('ffprobe failed: ' + (result.error?.message || result.stderr));
  const info = JSON.parse(result.stdout);
  const video = info.streams.find(s => s.codec_type === 'video');
  const audio = info.streams.find(s => s.codec_type === 'audio');
  if (!video) throw new Error('output has no video stream');
  const fps = numberOfRate(video.avg_frame_rate);
  const actualDuration = Number(video.duration || info.format.duration);
  const failures = [];
  if (video.codec_name !== 'h264') failures.push('codec must be H.264');
  if (video.width !== task.width || video.height !== task.height) failures.push('wrong video dimensions');
  if (Math.abs(fps - task.fps) > 0.01) failures.push('wrong frame rate');
  if (Math.abs(actualDuration - duration) > Math.max(0.12, 2 / task.fps)) failures.push('wrong video duration');
  if (video.nb_frames && Math.abs(Number(video.nb_frames) - Math.round(duration * task.fps)) > 1) failures.push('wrong frame count');
  if (!audio) failures.push('output has no audio stream');
  if (audio && Math.abs(Number(audio.duration || info.format.duration) - duration) > 0.15) failures.push('wrong audio duration');
  if (failures.length) throw new Error('verification failed: ' + failures.join('; '));
  const decoded = spawnSync('ffmpeg', ['-v', 'error', '-i', file, '-f', 'null', '-'], { encoding: 'utf8' });
  if (decoded.error || decoded.status !== 0 || decoded.stderr.trim()) throw new Error('media decoding failed: ' + (decoded.error?.message || decoded.stderr));
  const summary = { file, duration: actualDuration, width: video.width, height: video.height, fps, codec: video.codec_name, audio: audio.codec_name };
  console.log('Verified: ' + JSON.stringify(summary));
  return summary;
}
function main() {
  const [projectArgument, ...values] = process.argv.slice(2);
  if (projectArgument === '--help') {
    console.log('node render_mv.mjs PROJECT --sheet=0,1,2 | --strip=0:0.5 | --clip [--range=0:1] | --frames | --encode | --verify=out/video.mp4');
    return;
  }
  const project = resolve(projectArgument || '.');
  const taskFile = resolve(project, 'mv-task.json');
  if (!existsSync(taskFile)) throw new Error('project must contain mv-task.json: ' + taskFile);
  const task = JSON.parse(readFileSync(taskFile, 'utf8').replace(/^\uFEFF/, ''));
  const args = parseArgs(values);
  if (args.verify) {
    const file = resolve(project, args.verify === true ? 'out/video.mp4' : args.verify);
    verifyMedia(file, task);
    return;
  }
  const actions = ['sheet', 'strip', 'stills', 'clip', 'frames', 'encode'].filter(key => args[key] !== undefined);
  if (actions.length !== 1) throw new Error('choose exactly one render action; use --help');
  if (args.fps !== undefined && Number(args.fps) !== task.fps) throw new Error('frame rate must match mv-task.json');
  const action = actions[0];
  let duration = task.duration;
  const range = args.range || (typeof args.clip === 'string' ? args.clip : null);
  if (range) {
    const [a, b] = String(range).split(':').map(Number);
    if (!Number.isFinite(a) || !Number.isFinite(b) || a < 0 || b <= a || b > task.duration) throw new Error('invalid render range');
    duration = b - a;
  }
  const relativeDefault = action === 'sheet' || action === 'strip' ? 'out/check/' + action + '.jpg' : action === 'stills' ? 'out/stills' : 'out/video.mp4';
  const output = resolve(project, String(args.out || relativeDefault));
  const outputRelative = relative(project, output);
  if (outputRelative === '..' || outputRelative.startsWith('..' + (process.platform === 'win32' ? '\\' : '/')) || isAbsolute(outputRelative)) throw new Error('output must stay inside the project');
  if (action !== 'frames' && existsSync(output) && !args.overwrite) throw new Error('output exists; choose another --out or use --overwrite: ' + output);
  mkdirSync(dirname(output), { recursive: true });
  const cache = resolve(project, '.cache');
  mkdirSync(cache, { recursive: true });
  const candidate = args.chrome || task.browser || process.env.CHROME_PATH;
  if (!candidate || !existsSync(String(candidate))) throw new Error('Chrome not found; set CHROME_PATH or pass --chrome=<absolute path>');
  const forwarded = [];
  for (const [key, value] of Object.entries(args)) {
    if (['out', 'overwrite', 'chrome', 'verify'].includes(key)) continue;
    forwarded.push(value === true ? '--' + key : '--' + key + '=' + value);
  }
  forwarded.push('--chrome=' + candidate, '--fps=' + task.fps);
  if (action !== 'frames') forwarded.push('--out=' + output);
  if ((action === 'encode' || action === 'clip') && args.audio === undefined) forwarded.push('--audio=' + task.audio_clip);
  if (action === 'encode') {
    const framesDir = resolve(project, 'out/frames');
    if (!existsSync(framesDir)) throw new Error('render frames before encoding');
    const expected = Math.round(task.duration * task.fps);
    const frames = readdirSync(framesDir).filter(name => /^f\d{5}\.jpg$/.test(name));
    if (frames.length !== expected || !Array.from({ length: expected }, (_, i) => 'f' + String(i).padStart(5, '0') + '.jpg').every(name => frames.includes(name))) {
      throw new Error('frame sequence is incomplete or stale; expected ' + expected + ' consecutive frames from f00000.jpg');
    }
  }
  const result = spawnSync(process.execPath, [resolve(project, 'render.mjs'), ...forwarded], {
    cwd: project, stdio: 'inherit',
    env: { ...process.env, CHROME_PATH: String(candidate), TMP: cache, TEMP: cache }
  });
  if (result.error || result.status !== 0) throw new Error('renderer failed: ' + (result.error?.message || result.status));
  if (action === 'clip' || action === 'encode') {
    verifyMedia(output, task, duration);
  }
}
try {
  main();
} catch (error) {
  console.error('music-mv render failed: ' + error.message);
  process.exitCode = 1;
}
