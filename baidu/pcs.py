# -*- coding: utf-8 -*-

import requests
import os
import json
import hashlib
import binascii


class Client(object):

    URI = {'file': 'https://pcs.baidu.com/rest/2.0/pcs/file',
           'quota': 'https://pcs.baidu.com/rest/2.0/pcs/quota',
           'thumbnail': 'https://pcs.baidu.com/rest/2.0/pcs/thumbnail',
           'stream': 'https://pcs.baidu.com/rest/2.0/pcs/stream',
           'cloud_dl': 'https://pcs.baidu.com/rest/2.0/pcs/services/cloud_dl'
           }

    def __init__(self, access_token, chunksize=4 * 1024 * 1024L):
        self.access_token = access_token
        self.chunksize = chunksize

    def info(self):
        params = {'method': 'info',
                  'access_token': self.access_token
                  }
        r = requests.get(self.URI['quota'], params=params)
        return r.status_code, r.json()

    def upload_single(self, path, file, ondup='overwrite'):
        params = {'method': 'upload',
                  'access_token': self.access_token,
                  'path': path,
                  'ondup': ondup}

        with open(file, 'rb') as f:
            files = {'file': f}
            r = requests.post(self.URI['file'],
                              params=params,
                              files=files)

        return r.status_code, r.json()

    def _upload_tmp(self, f, offset, size):
        params = {'method': 'upload',
                  'access_token': self.access_token,
                  'type': 'tmpfile'}
        f.seek(offset)
        files = {'file': f.read(size)}
        r = requests.post(self.URI['file'],
                          params=params,
                          files=files)

        return r.status_code, r.json()

    def upload_multi(self, file, chunksize=1024 * 1024):
        size = os.path.getsize(file)
        if size <= chunksize or size > 1024L * chunksize:
            # TODO
            raise Exception("...")

        block_list = []
        with open(file, 'rb') as f:
            offset = 0
            while offset < size:
                code, result = self._upload_tmp(f, offset, chunksize)
                if code == requests.codes.ok:
                    block_list.append(result['md5'])
                    offset += chunksize
                else:
                    # TODO
                    raise Exception("...")

        return block_list

    def create_superfile(self, path, file, block_list, ondup='overwrite'):
        params = {'method': 'createsuperfile',
                  'access_token': self.access_token,
                  'path': path,
                  'ondup': ondup}

        r = requests.post(
            self.URI['file'],
            params=params,
            data={'param': json.dumps({'block_list': block_list})}
        )

        return r.status_code, r.json()

    def upload(self, path, file, ondup='overwrite'):
        size = os.path.getsize(file)
        if size <= self.chunksize:
            return self.upload_single(path, file, ondup)

        chunksize = self.chunksize
        while size > 1024 * chunksize:
            chunksize *= 2

        block_list = self.upload_multi(file, chunksize)
        return self.create_superfile(path, file, block_list, ondup)

    def delete(self, path):
        if type(path) is list:
            return self._delete_multi(path)
        else:
            return self._delete_single(path)

    def _delete_single(self, path):
        params = {'method': 'delete',
                  'access_token': self.access_token,
                  'path': path}
        r = requests.post(self.URI['file'],
                          params=params)

        return r.status_code, r.json()

    def _delete_multi(self, path):
        params = {'method': 'delete',
                  'access_token': self.access_token}
        paths = {'list': [{'path': p} for p in path]}
        r = requests.post(self.URI['file'],
                          params=params,
                          data={'param': json.dumps(paths)})

        return r.status_code, r.json()

    def read(self, path, range=None, stream=False, bucksize=64 * 1024L):
        params = {'method': 'download',
                  'access_token': self.access_token,
                  'path': path}
        headers = {}
        if type(range) is tuple or type(range) is list:
            start, end = 0, 0
            if len(range) >= 1:
                start = int(range[0])
            if len(range) >= 2:
                end = int(range[1])
            ran = end and 'bytes=%d-%d' % (start, end) or 'bytes=%d-' % (start)
            headers = {'Range': ran}
        r = requests.get(self.URI['file'],
                         params=params,
                         headers=headers,
                         stream=stream)

        if stream:
            return r.status_code, r.iter_content(bucksize)
        else:
            return r.status_code, r.content

    def download(self, path, file=None):
        if file is None:
            file = os.path.split(path)[1]
        code, meta = self.meta(path)
        if code != requests.codes.ok:
            # TODO
            raise Exception("...")
        meta = meta['list'][0]
        if 'isdir' in meta and meta['isdir'] == 0:
            size = meta['size']
            if size > self.chunksize:
                start, end = 0L, self.chunksize
                with open(file, 'wb') as f:
                    while start < size:
                        code, content = self.read(path, range=(
                            start, end - 1), stream=True)
                        if code == requests.codes.partial:
                            for c in content:
                                f.write(c)
                        else:
                            # TODo
                            raise Exception('...')

                        start = end
                        end += self.chunksize
                        if end >= size:
                            end = size
            else:
                code, content = self.read(path, stream=True)
                if code == requests.codes.ok:
                    with open(file, 'wb') as f:
                        for c in content:
                            f.write(c)
                else:
                    # TODO
                    raise Exception('...')

            return file
        # TODO isdir = 1 ??

    def meta(self, path):

        if type(path) is str or type(path) is unicode:
            return self._meta_single(path)
        elif type(path) is list:
            return self._meta_multi(path)

    def _meta_single(self, path):
        params = {'method': 'meta',
                  'access_token': self.access_token,
                  'path': path}

        r = requests.get(self.URI['file'],
                         params=params)

        return r.status_code, r.json()

    def _meta_multi(self, path):
        l = [{'path': f} for f in path]
        params = {'method': 'meta',
                  'access_token': self.access_token}

        r = requests.post(self.URI['file'],
                          params=params,
                          data={'param': json.dumps({'list': l})})

        return r.status_code, r.json()

    def mkdir(self, path):
        params = {'method': 'mkdir',
                  'access_token': self.access_token,
                  'path': path}
        r = requests.post(self.URI['file'],
                          params=params)

        return r.status_code, r.json()

    def list(self, path, by=None, order=None, limit=None):
        params = {'method': 'list',
                  'access_token': self.access_token,
                  'path': path}
        if by is not None:
            params['by'] = by
        if order is not None:
            params['order'] = order
        if limit is not None:
            params['limit'] = limit
        r = requests.get(self.URI['file'],
                         params=params)
        return r.status_code, r.json()

    def move(self, from_path, to_path):
        return self._op(method='move', from_path=from_path, to_path=to_path)

    def copy(self, from_path, to_path):
        return self._op(method='copy', from_path=from_path, to_path=to_path)

    def _op(self, method, from_path, to_path):
        if type(from_path) is list and type(to_path) is list:
            return self._op_multi(method, from_path, to_path)
        else:
            return self._op_single(method, from_path, to_path)

    def _op_single(self, method, from_path, to_path):
        params = {'method': method,
                  'access_token': self.access_token,
                  'from': from_path,
                  'to': to_path}
        r = requests.post(self.URI['file'],
                          params=params)

        return r.status_code, r.json()

    def _op_multi(self, method, from_path, to_path):
        params = {'method': method, 'access_token': self.access_token}
        l = {'list': [{'from': f, 'to': t}
                      for f, t in zip(from_path, to_path)]}
        r = requests.post(self.URI['file'],
                          params=params,
                          data={'param': json.dumps(l)})

        return r.status_code, r.json()

    def search(self, path, wd, re=0):
        params = {'method': 'search',
                  'access_token': self.access_token,
                  'path': path,
                  'wd': wd,
                  're': str(re)}
        r = requests.get(self.URI['file'],
                         params=params)

        return r.status_code, r.json()

    def thumbnail(self, path, width, height, quality=100):
        params = {'method': 'generate',
                  'access_token': self.access_token,
                  'path': path,
                  'width': int(width),
                  'height': int(height),
                  'quality': int(quality)}
        r = requests.get(self.URI['thumbnail'],
                         params=params)

        return r.status_code, r.content

    def diff(self, cursor='null'):
        params = {'method': 'diff',
                  'access_token': self.access_token,
                  'cursor': cursor}
        r = requests.get(self.URI['file'],
                         params=params)

        return r.status_code, r.json()

    def streaming(self, path, type='M3U8_320_240', stream=False,
                  bucksize=64 * 1024):
        params = {'method': 'streaming',
                  'access_token': self.access_token,
                  'path': path,
                  'type': type}
        r = requests.get(self.URI['file'],
                         params=params,
                         stream=stream)

        if stream:
            return r.status_code, r.iter_content(bucksize)
        else:
            return r.status_code, r.content

    def stream_list(self, type='image', start=0, limit=1000, filter_path=None):
        params = {'method': 'list',
                  'access_token': self.access_token,
                  'type': type,
                  'start': str(start),
                  'limit': str(limit)}
        if filter_path is not None:
            params['filter_path'] = filter_path
        r = requests.get(self.URI['stream'],
                         params=params)

        return r.status_code, r.json()

    def stream_download(self, path, stream=False, bucksize=64 * 1024):
        params = {'method': 'download',
                  'access_token': self.access_token,
                  'path': path}
        r = requests.get(self.URI['stream'],
                         params=params,
                         stream=stream)

        if stream:
            return r.status_code, r.iter_content(bucksize)
        else:
            return r.status_code, r.content

    def rapid_upload(self, path, content_legnth, content_md5, slice_md5,
                     content_crc32, ondup='overwrite'):
        params = {'method': 'rapidupload',
                  'access_token': self.access_token,
                  'path': path,
                  'content-length': content_legnth,
                  'content-md5': content_md5,
                  'slice-md5': slice_md5,
                  'content-crc32': content_crc32,
                  'ondup': ondup}
        r = requests.post(self.URI['file'],
                          params=params)

        return r.status_code, r.json()

    def rapid_upload_file(self, path, file, ondup='overwrite'):
        with open(file, 'rb') as f:
            md5 = hashlib.md5()
            slice_md5 = None
            crc = None
            for chunk in iter(lambda: f.read(256 * 1024L), b''):
                md5.update(chunk)
                if slice_md5 is None:
                    slice_md5 = md5.hexdigest()
                if crc is None:
                    crc = binascii.crc32(chunk)
                else:
                    crc = binascii.crc32(chunk, crc)
            content_md5 = md5.hexdigest()
            content_crc32 = '%08x' % (crc & 0xffffffff)
            content_length = str(f.tell())

        return self.rapid_upload(path,
                                 content_length,
                                 content_md5,
                                 slice_md5,
                                 content_crc32,
                                 ondup)

    def add_task(self, save_path, source_url, rate_limit=None, timeout=None,
                 callback=None, expires=None):
        params = {'method': 'add_task',
                  'access_token': self.access_token,
                  'save_path': save_path,
                  'source_url': source_url}
        if rate_limit is not None:
            params['rate_limit'] = int(rate_limit)
        if timeout is not None:
            params['timeout'] = int(timeout)
        if callback is not None:
            params['callback'] = callback
        if expires is not None:
            params['expires'] = int(expires)
        r = requests.post(self.URI['cloud_dl'],
                          params=params)

        return r.status_code, r.json()

    def query_task(self, task_ids, op_type=1, expires=None):
        params = {'method': 'query_task',
                  'access_token': self.access_token,
                  'op_type': int(op_type)}
        if type(task_ids) is list or type(task_ids) is tuple:
            task_ids = ','.join(map(str, task_ids))
        params['task_ids'] = str(task_ids)
        if expires is not None:
            params['expires'] = int(expires)
        r = requests.post(self.URI['cloud_dl'],
                          params=params)

        return r.status_code, r.json()

    def list_task(self, expires=None, start=0, limit=10, asc=0,
                  source_url=None, save_path=None, create_time=None,
                  status=None, need_task_info=1):
        params = {'method': 'list_task',
                  'access_token': self.access_token,
                  'start': int(start),
                  'limit': int(limit),
                  'asc': int(asc),
                  'need_task_info': int(need_task_info)}
        if expires is not None:
            params['expires'] = int(expires)
        if source_url is not None:
            params['source_url'] = source_url
        if save_path is not None:
            params['save_path'] = save_path
        if create_time is not None:
            params['create_time'] = int(create_time)
        if status is not None:
            params['status'] = int(status)
        r = requests.post(self.URI['cloud_dl'],
                          params=params)

        return r.status_code, r.json()

    def cancel_task(self, task_id, expires=None):
        params = {'method': 'list_task',
                  'access_token': self.access_token,
                  'task_id': task_id}
        if expires is not None:
            params['expires'] = int(expires)
        r = requests.post(self.URI['cloud_dl'], params=params)

        return r.status_code, r.json()

    def list_recycle(self, start=0, limit=1000):
        params = {'method': 'listrecycle',
                  'access_token': self.access_token,
                  'start': start,
                  'limit': limit}
        r = requests.get(self.URI['file'], params=params)

        return r.status_code, r.json()

    def restore_recycle(self, fs_id):
        params = {'method': 'restore',
                  'access_token': self.access_token}
        data = None
        if type(fs_id) is list or type(fs_id) is tuple:
            data = {'param': json.dumps({'list': [{'fs_id': fid} for fid in fs_id]})}
        else:
            params['fs_id'] = str(fs_id)

        r = requests.post(self.URI['file'], params=params, data=data)

        return r.status_code, r.json()

    def empty_recycle(self):
        params = {'method': 'delete',
                  'access_token': self.access_token,
                  'type': 'recycle'}
        r = requests.post(self.URI['file'], params=params)

        return r.status_code, r.json()
