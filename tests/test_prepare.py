import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/music-mv'
SCRIPT = SKILL / 'scripts/prepare_mv.py'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys_cache = ROOT / 'test-tmp'
sys_cache.mkdir(exist_ok=True)


def module(test):
    test.assertTrue(SCRIPT.is_file(), 'MV preparation helper has not been implemented')
    spec = importlib.util.spec_from_file_location('prepare_mv', SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class PreparationTests(unittest.TestCase):
    def test_timestamps_preserve_exact_interval(self):
        m = module(self)
        self.assertEqual(m.parse_time('00:39.000'), 39)
        self.assertEqual(m.parse_time('01:07'), 67)
        self.assertEqual(m.parse_time('1:02:03.125'), 3723.125)
        self.assertEqual(m.parse_time(39.62), 39.62)
        for invalid in ('1:60', '-1', 'nan', 'inf', 'abc', True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                m.parse_time(invalid)

    def test_lrc_metadata_multitags_and_positive_offset(self):
        m = module(self)
        rows = m.parse_lrc('\ufeff[ar:artist]\n{"t":0,"c":[{"tx":"credits"}]}\n[00:39.620][00:41.820]测试\n[offset:+250]\n')
        self.assertEqual([round(r['time'], 3) for r in rows], [39.87, 42.07])
        self.assertEqual([r['text'] for r in rows], ['测试', '测试'])

    def test_crossing_start_and_end_keep_original_fill_time(self):
        m = module(self)
        rows = m.parse_lrc('[00:37.740]前一句\n[00:39.620]第一句\n[01:03.460]末句\n[01:07.690]下一句')
        clipped = m.clip_lyrics(rows, 39, 67, 220)
        self.assertAlmostEqual(clipped[0]['start'], 0)
        self.assertAlmostEqual(clipped[0]['line_start'], -1.26)
        self.assertAlmostEqual(clipped[0]['end'], .62)
        self.assertAlmostEqual(clipped[-1]['end'], 28)
        self.assertAlmostEqual(clipped[-1]['line_end'], 28.69)
        self.assertEqual([r['text'] for r in clipped], ['前一句', '第一句', '末句'])

    def test_line_at_end_is_excluded(self):
        m = module(self)
        rows = m.parse_lrc('[00:39]A\n[01:07]B')
        self.assertEqual([r['text'] for r in m.clip_lyrics(rows, 39, 67, 80)], ['A'])

    def test_empty_timed_line_ends_preceding_lyric(self):
        m = module(self)
        rows = m.parse_lrc('[00:39]A\n[00:40]\n[00:42]B')
        clips = m.clip_lyrics(rows, 39, 44, 50)
        self.assertEqual(clips[0]['end'], 1)
        self.assertEqual(clips[1]['start'], 3)

    def test_multiple_simultaneous_lines_are_kept(self):
        m = module(self)
        rows = m.parse_lrc('[00:39]原文\n[00:39]译文\n[00:42]下一行')
        clips = m.clip_lyrics(rows, 39, 44, 50)
        self.assertEqual(clips[0]['text'], '原文 / 译文')
        self.assertEqual(clips[0]['end'], 3)

    def test_bpm_phase_remains_relative_to_source(self):
        m = module(self)
        self.assertAlmostEqual(m.clip_beat_offset(39, 120, .2), .2)
        self.assertAlmostEqual(m.clip_beat_offset(39.1, 120, .2), .1)

    def test_many_lines_keep_clip_boundaries(self):
        m = module(self)
        timestamps = [37.74, 39.62, 41.82, 44.18, 46.53, 48.77, 49.98, 53.78, 56.19, 58.68, 61, 63.46, 67.69]
        text = '\n'.join(f'[{int(t//60):02}:{t%60:05.2f}]Line {i}' for i, t in enumerate(timestamps))
        clipped = m.clip_lyrics(m.parse_lrc(text), 39, 67, 219.626667)
        self.assertAlmostEqual(clipped[1]['start'], .62)
        self.assertAlmostEqual(clipped[-1]['start'], 24.46)
        self.assertEqual(len(clipped), 12)
        self.assertTrue(all(0 <= r['start'] < r['end'] <= 28 for r in clipped))

    def test_generated_lyrics_obey_renderer_array_contract(self):
        m = module(self)
        rows = m.clip_lyrics(m.parse_lrc('[00:37.740]A\n[00:39.620]B\n[01:03.460]C\n[01:07.690]D'), 39, 67, 220)
        template = SKILL / 'assets/painted-animation/template/src/karaoke.js'
        rendered = m._render_karaoke(template, rows)
        table = json.loads(rendered.split('const LY = ', 1)[1].split(';', 1)[0])
        self.assertAlmostEqual(table[0][0], -1.26)
        self.assertAlmostEqual(table[0][3]['sing'], 1.88)
        self.assertEqual(table[-1][1], 28)
        self.assertAlmostEqual(table[-1][3]['sing'], 4.23)
        self.assertIn('window.overlayHook', rendered)

    def test_missing_inputs_fail_before_output_creation(self):
        m = module(self)
        scratch = ROOT / 'test-tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            target = Path(directory) / 'not-created'
            request = dict(image='missing.png', audio='missing.mp3', lyrics='missing.lrc', start=39, end=67, style='小镇姑娘', output=str(target))
            with self.assertRaises(ValueError):
                m.validate_request(request, Path(directory))
            self.assertFalse(target.exists())

    def test_bad_range_and_existing_project_are_rejected(self):
        m = module(self)
        with tempfile.TemporaryDirectory(dir=sys_cache) as directory:
            project = Path(directory)
            for name in ('character.png', 'song.mp3', 'song.lrc'):
                (project/name).write_bytes(b'fixture')
            request = dict(image=str(project/'character.png'), audio=str(project/'song.mp3'), lyrics=str(project/'song.lrc'), start=67, end=39, style='watercolor')
            with self.assertRaises(ValueError):
                m.validate_request(request, project)
            request.update(start=39, end=67, output=str(project/'existing-project'))
            (project/'existing-project').mkdir()
            with self.assertRaises(FileExistsError):
                m.validate_request(request, project)


class RenderEntryTests(unittest.TestCase):
    def run_entry(self, directory, *options):
        project = Path(directory)
        task = dict(duration=28, width=1920, height=1080, fps=24, audio_clip=str(project/'assets/clip.m4a'))
        (project/'mv-task.json').write_text(json.dumps(task), encoding='utf-8')
        script = SKILL / 'scripts/render_mv.mjs'
        return subprocess.run(['node', str(script), str(project), *options], capture_output=True, text=True, encoding='utf-8')

    def test_missing_project_reports_failure(self):
        script = SKILL / 'scripts/render_mv.mjs'
        self.assertTrue(script.is_file(), 'MV render entry has not been implemented')
        result = subprocess.run(['node', str(script), str(ROOT/'missing-project'), '--clip'], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('mv-task.json', result.stderr)

    def test_missing_browser_is_reported(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'test-tmp') as directory:
            result = self.run_entry(directory, '--clip', '--chrome=' + str(Path(directory)/'missing.exe'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Chrome not found', result.stderr)

    def test_output_cannot_escape_project(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'test-tmp') as directory:
            result = self.run_entry(directory, '--clip', '--out=../escaped.mp4')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('inside the project', result.stderr)

    def test_video_is_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'test-tmp') as directory:
            video = Path(directory)/'existing.mp4'
            video.write_bytes(b'original')
            result = self.run_entry(directory, '--clip', '--out=existing.mp4')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('output exists', result.stderr)
            self.assertEqual(video.read_bytes(), b'original')

    def test_range_cannot_exceed_clip(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'test-tmp') as directory:
            result = self.run_entry(directory, '--clip', '--range=0:29')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('invalid render range', result.stderr)


if __name__ == '__main__':
    unittest.main()
