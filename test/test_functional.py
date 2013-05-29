# -*- coding: utf-8 -*-
''' Functional test with real ACCESS_TOKEN and APP_FOLDER.
'''
import unittest
import baidu.pcs
import os
import hashlib
import tempfile
import requests
import datetime
import time


def md5sum(filename):
    md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def tmpname(prefix=None):
    name = datetime.datetime.now().strftime('%s')
    if prefix is not None:
        name = str(prefix) + name
    return name


class TestEnv(unittest.TestCase):

    def testAccessToken(self):
        self.assertTrue('ACCESS_TOKEN' in os.environ)
        self.assertTrue('APP_FOLDER' in os.environ)


class TestDelete(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.test_file = os.path.join(os.path.dirname(__file__),
                                      'res',
                                      'abc.txt')
        path = os.environ['APP_FOLDER'] + '/delete_abc.txt'
        filename = self.test_file
        self.paths = [r['path'] for c, r in [self.yun.upload_single(
            path=path, file=filename, ondup='newcopy') for i in range(5)]]

    def tearDown(self):
        self.yun.delete(self.paths)

    def test_delete(self):
        code, r = self.yun.delete(self.paths[0])
        self.assertTrue('request_id' in r.keys() and len(r.keys()) == 1)
        self.assertEqual(code, requests.codes.ok)

        code, r = self.yun.delete(self.paths[1:])
        self.assertTrue('request_id' in r.keys() and len(r.keys()) == 1)
        self.assertEqual(code, requests.codes.ok)


class TestInfoAPI(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])

    def test_info(self):
        code, r = self.yun.info()
        keys = ['quota', 'used', 'request_id']
        for k in keys:
            self.assertTrue(k in r)
        self.assertEqual(code, requests.codes.ok)


class TestUploadAPI(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.test_file = os.path.join(os.path.dirname(__file__),
                                      'res',
                                      '1.jpg')
        self.test_big_file = os.path.join(os.path.dirname(__file__),
                                          'res',
                                          'big.jpg')
        self.uploaded = []

    def tearDown(self):
        for f in self.uploaded:
            self.yun.delete(f)

    def test_upload_single(self):
        keys = ['path', 'size', 'ctime', 'mtime', 'md5', 'fs_id', 'request_id']
        path = os.environ['APP_FOLDER'] + '/1_test_upload_single.jpg'
        filename = self.test_file
        code, r = self.yun.upload_single(path=path, file=filename)
        self.assertTrue(code, requests.codes.ok)
        self.uploaded.append(r['path'])
        for k in keys:
            self.assertTrue(k in r)
        self.assertEqual(r['md5'], md5sum(filename))
        old_path = r['path']

        code, r = self.yun.upload_single(path=path, file=filename,
                                         ondup='newcopy')
        self.assertTrue(code, requests.codes.ok)
        self.uploaded.append(r['path'])
        for k in keys:
            self.assertTrue(k in r)
        new_path = r['path']
        self.assertNotEqual(new_path, old_path)
        self.assertEqual(r['md5'], md5sum(filename))

    def test_upload(self):
        keys = ['path', 'size', 'ctime', 'mtime', 'md5', 'fs_id', 'request_id']
        path = os.environ['APP_FOLDER'] + '/big_test_upload.jpg'
        filename = self.test_big_file
        self.yun.chunksize = 1024L * 1024
        self.assertTrue(os.path.getsize(filename) > self.yun.chunksize)
        code, r = self.yun.upload(path=path, file=filename)
        self.assertTrue(code, requests.codes.ok)
        self.uploaded.append(r['path'])
        for k in keys:
            self.assertTrue(k in r)
        # self.assertEqual(r['md5'], md5sum(filename))

        path = os.environ['APP_FOLDER'] + '/1_test_upload.jpg'
        filename = self.test_file
        self.assertTrue(os.path.getsize(filename) <= self.yun.chunksize)
        code, r = self.yun.upload(path=path, file=filename)
        self.assertTrue(code, requests.codes.ok)
        self.uploaded.append(r['path'])
        for k in keys:
            self.assertTrue(k in r)
        self.assertEqual(r['md5'], md5sum(filename))

    def test_upload_multi(self):
        keys = ['path', 'size', 'ctime', 'mtime', 'md5', 'fs_id', 'request_id']
        path = os.environ['APP_FOLDER'] + '/big_test_upload_multi.jpg'
        filename = self.test_big_file
        size = os.path.getsize(filename)
        chunksize = 1024 * 1024
        chunks = size / chunksize + (size % chunksize and 1 or 0)

        r = self.yun.upload_multi(filename, chunksize)
        self.assertTrue(type(r) is list and len(r) == chunks)

        code, r = self.yun.create_superfile(
            path=path, file=filename, block_list=r)
        self.assertTrue(code, requests.codes.ok)
        self.uploaded.append(r['path'])
        for k in keys:
            self.assertTrue(k in r)
        # self.assertEqual(r['md5'], md5sum(filename))


class TestMeta(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.abc_file = os.path.join(os.path.dirname(__file__),
                                     'res',
                                     'abc.txt')
        path = os.environ['APP_FOLDER'] + '/abc_download.txt'
        code, r = self.yun.upload(path=path, file=self.abc_file)
        self.file_path = r['path']
        code, r = self.yun.mkdir(os.environ[
                                 'APP_FOLDER'] + '/' + tmpname('dir'))
        self.dir_path = r['path']

    def tearDown(self):
        self.yun.delete(path=self.file_path)
        self.yun.delete(path=self.dir_path)

    def testMeta(self):
        code, r = self.yun.meta(self.file_path)
        self.assertTrue(code, requests.codes.ok)
        meta = r['list'][0]
        self.assertEqual(meta['isdir'], 0)
        self.assertEqual(meta['size'], os.path.getsize(self.abc_file))

        code, r = self.yun.meta(self.dir_path)
        self.assertTrue(code, requests.codes.ok)
        meta = r['list'][0]
        self.assertEqual(meta['isdir'], 1)

    def testMetaMulti(self):
        code, r = self.yun.meta([self.file_path, self.dir_path])
        self.assertTrue(code, requests.codes.ok)
        metas = r['list']
        self.assertEqual(len(metas), 2)
        self.assertEqual(metas[0]['isdir'], 0)
        self.assertEqual(metas[1]['isdir'], 1)


class TestReadContent(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.abc_file = os.path.join(os.path.dirname(__file__),
                                     'res',
                                     'abc.txt')
        path = os.environ['APP_FOLDER'] + '/abc_download.txt'
        code, r = self.yun.upload(path=path, file=self.abc_file)
        self.path = r['path']
        with open(self.abc_file) as f:
            self.content = f.read()

    def tearDown(self):
        self.yun.delete(path=self.path)

    def testRead(self):
        code, content = self.yun.read(path=self.path)
        self.assertTrue(code, requests.codes.ok)
        self.assertEqual(self.content, content)

    def testReadByStream(self):
        code, content = self.yun.read(path=self.path, stream=True)
        self.assertTrue(code, requests.codes.ok)
        buf = bytearray()
        for c in content:
            buf += c
        self.assertEqual(self.content, buf)

    def testReadRange(self):
        range = (0,)
        code, content = self.yun.read(path=self.path, range=range)
        self.assertTrue(code, requests.codes.partial)
        self.assertEqual(self.content, content)

        range = (len(self.content) / 2,)
        code, content = self.yun.read(path=self.path, range=range)
        self.assertTrue(code, requests.codes.partial)
        self.assertEqual(self.content[range[0]:], content)

        range = (len(self.content) / 10, len(self.content) / 2)
        code, content = self.yun.read(path=self.path, range=range)
        self.assertTrue(code, requests.codes.partial)
        self.assertEqual(self.content[range[0]:range[1] + 1], content)

    def testDownload(self):
        fh, fn = tempfile.mkstemp()
        self.yun.download(path=self.path, file=fn)
        self.assertEqual(md5sum(self.abc_file), md5sum(fn))
        os.remove(fn)


class TestMkdir(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.path = os.environ['APP_FOLDER'] + \
            '/' + tmpname('tmp')
        self.abc_file = os.path.join(os.path.dirname(__file__),
                                     'res',
                                     'abc.txt')

    def tearDown(self):
        self.yun.delete(self.path)

    def testMkdir(self):
        code, r = self.yun.mkdir(path=self.path)
        self.assertEqual(code, requests.codes.ok)
        self.assertTrue('path' in r)


class TestList(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.path = os.environ['APP_FOLDER'] + \
            '/' + tmpname('tmp_')
        self.yun.mkdir(path=self.path)
        abc_file = os.path.join(os.path.dirname(__file__),
                                'res',
                                'abc.txt')
        self.files = map(lambda r: r[1]['path'],
                         [self.yun.upload(path=self.path + '/%d.txt' % i, file=abc_file) for i in range(5)])

    def tearDown(self):
        map(lambda p: self.yun.delete(path=p), self.files)
        self.yun.delete(self.path)

    def testList(self):
        c, r = self.yun.list(path=self.path)
        self.assertEqual(c, requests.codes.ok)
        self.assertEqual(len(r['list']), len(self.files))

        c, r = self.yun.list(
            path=self.path, by='name', order='asc', limit='1-3')
        self.assertEqual(c, requests.codes.ok)
        self.assertEqual(len(r['list']), 2)


class TestMoveSingle(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.from_path = os.environ['APP_FOLDER'] + '/' + tmpname('from')
        self.to_path = os.environ['APP_FOLDER'] + '/' + tmpname('to')
        self.yun.mkdir(path=self.from_path)

    def tearDown(self):
        self.yun.delete(self.from_path)
        self.yun.delete(self.to_path)

    def testMoveSingle(self):
        c, r = self.yun.move(from_path=self.from_path, to_path=self.to_path)
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('extra' in r and 'list' in r['extra'] and 'from' in r[
                        'extra']['list'][0] and 'to' in r['extra']['list'][0])


class TestMoveCopy(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.from_path = os.environ['APP_FOLDER'] + '/' + tmpname('from')
        self.to_path = os.environ['APP_FOLDER'] + '/' + tmpname('to')
        self.new_path = os.environ['APP_FOLDER'] + '/' + tmpname('n')
        self.yun.mkdir(path=self.from_path)
        self.yun.mkdir(path=self.to_path)

        self.paths = ["%d" % i for i in range(5)]
        for f in self.paths:
            self.yun.mkdir(self.from_path + '/' + f)

    def tearDown(self):
        self.yun.delete(self.from_path)
        self.yun.delete(self.to_path)
        self.yun.delete(self.new_path)

    def testMoveSingle(self):
        c, r = self.yun.move(from_path=self.from_path, to_path=self.new_path)
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('extra' in r and 'list' in r['extra'] and 'from' in r[
                        'extra']['list'][0] and 'to' in r['extra']['list'][0])

    def testMoveMulti(self):
        from_path = ['%s/%s' % (self.from_path, f) for f in self.paths]
        to_path = ['%s/%s' % (self.to_path, f) for f in self.paths]
        c, r = self.yun.move(from_path=from_path, to_path=to_path)
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('extra' in r and
                        'list' in r['extra'] and
                        len(r['extra']['list']) == len(self.paths))

    def testCopySingle(self):
        c, r = self.yun.copy(from_path=self.from_path, to_path=self.new_path)
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('extra' in r and 'list' in r['extra'] and 'from' in r[
                        'extra']['list'][0] and 'to' in r['extra']['list'][0])


class TestSearch(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.test_file = os.path.join(os.path.dirname(__file__),
                                      'res',
                                      'abc.txt')
        self.path = os.environ['APP_FOLDER']
        path = self.path + '/search_abc.txt'
        filename = self.test_file
        self.files = [r['path'] for c, r in [self.yun.upload_single(
            path=path, file=filename, ondup='newcopy') for i in range(5)]]

    def tearDown(self):
        self.yun.delete(self.files)

    def test_search(self):
        code, r = self.yun.search(path=self.path, wd='abc', re=0)
        self.assertTrue('list' in r)
        self.assertEqual(code, requests.codes.ok)


class TestThumbnail(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.img_file = os.path.join(os.path.dirname(__file__),
                                     'res',
                                     '1.jpg')
        self.path = os.environ['APP_FOLDER']
        path = self.path + '/test_thumbnail.jpg'
        filename = self.img_file
        c, r = self.yun.upload_single(path=path, file=filename)
        self.file = r['path']

    def tearDown(self):
        self.yun.delete(self.file)

    def test_thumbnail(self):
        code, r = self.yun.thumbnail(path=self.file, width='480', height='320')
        self.assertEqual(code, requests.codes.ok)


class TestNoSetup(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])

    def tearDown(self):
        pass

    def test_diff(self):
        code, r = self.yun.diff()
        self.assertEqual(code, requests.codes.ok)
        keys = ['entries', 'has_more', 'reset', 'cursor']
        for k in keys:
            self.assertTrue(k in r.keys())

        code, r = self.yun.diff(cursor=r['cursor'])
        self.assertEqual(code, requests.codes.ok)
        keys = ['entries', 'has_more', 'reset', 'cursor']
        for k in keys:
            self.assertTrue(k in r.keys())

    def test_stream_list(self):
        code, r = self.yun.stream_list(type='image')
        self.assertEqual(code, requests.codes.ok)
        keys = ['start', 'total', 'limit', 'list']
        for k in keys:
            self.assertTrue(k in r.keys())
        self.assertTrue(type(r['list']) is list)

        code, r = self.yun.stream_list(type='video',
                                       filter_path='/apps/screenshot')
        self.assertEqual(code, requests.codes.ok)
        keys = ['start', 'total', 'limit', 'list']
        for k in keys:
            self.assertTrue(k in r.keys())
        self.assertTrue(type(r['list']) is list)

        code, r = self.yun.stream_list(type='audio', start=5, limit=10)
        self.assertEqual(code, requests.codes.ok)
        keys = ['start', 'total', 'limit', 'list']
        for k in keys:
            self.assertTrue(k in r.keys())
        self.assertTrue(type(r['list']) is list)

        code, r = self.yun.stream_list(type='doc', start=0, limit=10)
        self.assertEqual(code, requests.codes.ok)
        keys = ['start', 'total', 'limit', 'list']
        for k in keys:
            self.assertTrue(k in r.keys())
        self.assertTrue(type(r['list']) is list)


class TestStreaming(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.video_file = os.path.join(os.path.dirname(__file__),
                                       'res',
                                       'clipcanvas_14348_H264_640x360.mp4')
        path = os.environ['APP_FOLDER'] + '/clipcanvas_14348_H264_640x360.mp4'
        c, r = self.yun.upload(path=path, file=self.video_file)
        self.path = r['path']

    def tearDown(self):
        self.yun.delete(path=self.path)

    def test_streaming_encode(self):
        code, r = self.yun.streaming(path=self.path)
        self.assertEqual(code, requests.codes.ok)
        self.assertTrue(len(r) > 0)

        code, r = self.yun.streaming(path=self.path, stream=True)
        self.assertEqual(code, requests.codes.ok)
        for c in r:
            self.assertTrue(len(c) > 0)

    def test_stream_download(self):
        code, r = self.yun.stream_download(path=self.path)
        self.assertEqual(code, requests.codes.ok)
        md5 = hashlib.md5()
        md5.update(r)
        self.assertEqual(md5.hexdigest(), md5sum(self.video_file))

        code, r = self.yun.stream_download(path=self.path, stream=True)
        self.assertEqual(code, requests.codes.ok)
        md5 = hashlib.md5()
        for c in r:
            md5.update(c)
        self.assertEqual(md5.hexdigest(), md5sum(self.video_file))


class TestRapidUpload(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.video_file = os.path.join(os.path.dirname(__file__),
                                       'res',
                                       'clipcanvas_14348_H264_640x360.mp4')
        path = os.environ['APP_FOLDER'] + '/clipcanvas_14348_H264_640x360.mp4'
        c, r = self.yun.upload(path=path, file=self.video_file)
        self.paths = [r['path']]

    def tearDown(self):
        time.sleep(1)  #非强一致接口，上传后请等待1秒后再读取
        self.yun.delete(path=self.paths)

    def test_rapid_upload(self):
        path = path = os.environ['APP_FOLDER'] + '/rapid_clipcanvas.mp4'
        c, r = self.yun.rapid_upload_file(path, self.video_file)
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('md5' in r)
        self.assertEqual(r['md5'], md5sum(self.video_file))

        self.paths.append(r['path'])


class TestAddCancelTask(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.url = 'http://www.w3.org/2013/Talks/0528-dsr-html5.pdf'
        self.path = os.environ['APP_FOLDER'] + '/' + tmpname('tmp_add_') + '.pdf'

    def tearDown(self):
        self.yun.delete(self.path)

    def test_add_and_delete_task(self):
        c, r = self.yun.add_task(save_path=self.path, source_url=self.url)
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('task_id' in r)

        c, r = self.yun.cancel_task(task_id=r['task_id'])
        self.assertTrue(c, requests.codes.ok)

    def test_add_task_params(self):
        c, r = self.yun.add_task(save_path=self.path,
                                 source_url=self.url,
                                 rate_limit=1024,
                                 timeout=1000)
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('task_id' in r)

        c, r = self.yun.cancel_task(task_id=r['task_id'])
        self.assertTrue(c, requests.codes.ok)


class TestTask(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.urls = [
            'http://tools.ietf.org/pdf/rfc1945.pdf',
            'http://tools.ietf.org/pdf/rfc2616.pdf',
            'http://tools.ietf.org/pdf/rfc6265.pdf']
        self.paths = []
        self.task_ids = []

        for url in self.urls:
            filename = os.environ['APP_FOLDER'] + '/' + tmpname('tmp_query_') + '.pdf'
            c, r = self.yun.add_task(save_path=filename, source_url=url)
            self.paths.append(filename)
            self.task_ids.append(r['task_id'])

    def tearDown(self):
        time.sleep(1)
        for task_id in self.task_ids:
            self.yun.cancel_task(task_id)
        time.sleep(1)
        self.yun.delete(self.paths)

    def test_query_task(self):
        c, r = self.yun.query_task(task_ids=self.task_ids, op_type=1)
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('task_info' in r and type(r['task_info']) is dict)
        self.assertEqual(len(self.task_ids), len(r['task_info'].keys()))

        c, r = self.yun.query_task(task_ids=self.task_ids[0], op_type=0)
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('task_info' in r and type(r['task_info']) is dict)
        self.assertEqual(1, len(r['task_info'].keys()))
        self.assertEqual(r['task_info'].keys()[0], str(self.task_ids[0]))

    def test_list_task(self):
        c, rl = self.yun.list_task()
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('task_info' in rl.keys() and
                        type(rl['task_info']) is list)

        c, rl = self.yun.list_task(start=10,
                                   limit=100,
                                   asc=1,
                                   source_url=self.urls[0],
                                   save_path=self.paths[0],
                                   create_time=long(
                                       datetime.datetime.now().strftime('%s')),
                                   status=1, need_task_info=0)
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('task_info' in rl.keys() and
                        type(rl['task_info']) is list)

        c, rl = self.yun.list_task(start=0,
                                   limit=10,
                                   asc=0,
                                   source_url=self.urls[0],
                                   save_path=self.paths[0],
                                   create_time=long(
                                       datetime.datetime.now().strftime('%s')),
                                   status=0, need_task_info=1)
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('task_info' in rl.keys() and
                        type(rl['task_info']) is list)


class TestRecycle(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])

    def test_list_recycle(self):
        c, r = self.yun.list_recycle()
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('list' in r and type(r['list']) is list)

    def test_empty_recycle(self):
        c, r = self.yun.empty_recycle()
        self.assertEqual(c, requests.codes.ok)


class TestRestoreRecycle(unittest.TestCase):

    def setUp(self):
        self.yun = baidu.pcs.Client(os.environ['ACCESS_TOKEN'])
        self.test_file = os.path.join(os.path.dirname(__file__),
                                      'res',
                                      'abc.txt')
        self.files = []
        for i in range(5):
            path = os.environ['APP_FOLDER'] + '/' + tmpname('recycle_') + '.txt'
            c, r = self.yun.upload(path=path, file=self.test_file)
            self.files.append((r['path'], r['fs_id']))
            self.yun.delete(r['path'])

    def tearDown(self):
        # 还原单个文件或目录（非强一致接口，调用后请sleep 1秒读取）
        self.yun.delete([f[0] for f in self.files])

    def test_restore_recycle(self):
        c, r = self.yun.restore_recycle(fs_id=self.files[0][1])
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('extra' in r and 'list' in r['extra'])

        c, r = self.yun.restore_recycle(fs_id=[f[1] for f in self.files[1:]])
        self.assertEqual(c, requests.codes.ok)
        self.assertTrue('extra' in r and 'list' in r['extra'])
