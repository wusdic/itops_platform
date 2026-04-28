"""
MinIO对象存储客户端核心实现

支持本地文件和MinIO云存储，提供统一的文件存储接口。
"""

import hashlib
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class LocalStorageClient:
    """本地文件系统存储客户端"""
    
    def __init__(self, base_path: str = '/tmp/storage'):
        """
        初始化本地存储客户端
        
        Args:
            base_path: 基础存储路径
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def upload_file(
        self,
        local_path: str,
        object_name: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        上传本地文件
        
        Args:
            local_path: 本地文件路径
            object_name: 对象名称（存储路径）
            metadata: 元数据
            
        Returns:
            上传结果
        """
        source = Path(local_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {local_path}")
        
        # 计算目标路径
        target = self.base_path / object_name
        target.parent.mkdir(parents=True, exist_ok=True)
        
        # 复制文件
        shutil.copy2(source, target)
        
        # 计算哈希
        hash_md5 = hashlib.md5()
        with open(target, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        
        return {
            'object_name': object_name,
            'size': target.stat().st_size,
            'etag': hash_md5.hexdigest(),
            'metadata': metadata or {}
        }
    
    def upload_data(
        self,
        data: bytes,
        object_name: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        上传数据内容
        
        Args:
            data: 字节数据
            object_name: 对象名称
            metadata: 元数据
            
        Returns:
            上传结果
        """
        target = self.base_path / object_name
        target.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target, 'wb') as f:
            f.write(data)
        
        hash_md5 = hashlib.md5(data).hexdigest()
        
        # 保存元数据
        if metadata:
            meta_file = target.with_suffix(target.suffix + '.meta')
            with open(meta_file, 'w') as f:
                json.dump(metadata, f)
        
        return {
            'object_name': object_name,
            'size': len(data),
            'etag': hash_md5,
            'metadata': metadata or {}
        }
    
    def download_file(self, object_name: str, local_path: str) -> str:
        """
        下载文件到本地
        
        Args:
            object_name: 对象名称
            local_path: 本地目标路径
            
        Returns:
            下载后的文件路径
        """
        source = self.base_path / object_name
        if not source.exists():
            raise FileNotFoundError(f"Object not found: {object_name}")
        
        target = Path(local_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source, target)
        return str(target)
    
    def download_data(self, object_name: str) -> bytes:
        """
        下载数据内容
        
        Args:
            object_name: 对象名称
            
        Returns:
            字节数据
        """
        source = self.base_path / object_name
        if not source.exists():
            raise FileNotFoundError(f"Object not found: {object_name}")
        
        with open(source, 'rb') as f:
            return f.read()
    
    def delete(self, object_name: str) -> bool:
        """删除对象"""
        target = self.base_path / object_name
        if target.exists():
            target.unlink()
            # 删除元数据文件
            meta_file = target.with_suffix(target.suffix + '.meta')
            if meta_file.exists():
                meta_file.unlink()
            return True
        return False
    
    def exists(self, object_name: str) -> bool:
        """检查对象是否存在"""
        return (self.base_path / object_name).exists()
    
    def list_objects(
        self,
        prefix: str = '',
        max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        列出对象
        
        Args:
            prefix: 前缀过滤
            max_keys: 最大返回数量
            
        Returns:
            对象列表
        """
        prefix_path = self.base_path / prefix
        objects = []
        
        for path in prefix_path.rglob('*'):
            if path.is_file() and not path.suffix.endswith('.meta'):
                rel_path = path.relative_to(self.base_path)
                
                # 读取元数据
                metadata = {}
                meta_file = path.with_suffix(path.suffix + '.meta')
                if meta_file.exists():
                    with open(meta_file) as f:
                        metadata = json.load(f)
                
                objects.append({
                    'object_name': str(rel_path),
                    'size': path.stat().st_size,
                    'last_modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    'metadata': metadata
                })
                
                if len(objects) >= max_keys:
                    break
        
        return objects
    
    def get_metadata(self, object_name: str) -> Dict[str, Any]:
        """获取对象元数据"""
        source = self.base_path / object_name
        if not source.exists():
            raise FileNotFoundError(f"Object not found: {object_name}")
        
        metadata = {}
        meta_file = source.with_suffix(source.suffix + '.meta')
        if meta_file.exists():
            with open(meta_file) as f:
                metadata = json.load(f)
        
        return {
            'size': source.stat().st_size,
            'last_modified': datetime.fromtimestamp(source.stat().st_mtime).isoformat(),
            'metadata': metadata
        }
    
    def health_check(self) -> bool:
        """健康检查"""
        return self.base_path.exists() and self.base_path.is_dir()


class MinIOClient:
    """
    MinIO/S3兼容对象存储客户端
    
    支持MinIO服务器和AWS S3，提供统一的文件存储接口。
    
    Attributes:
        endpoint: 服务端点
        access_key: 访问密钥
        secret_key: 秘密密钥
        secure: 是否使用HTTPS
        bucket: 默认存储桶
    """
    
    def __init__(
        self,
        endpoint: str = 'localhost:9000',
        access_key: str = 'minioadmin',
        secret_key: str = 'minioadmin',
        secure: bool = False,
        bucket: str = 'itops',
        region: str = 'us-east-1'
    ):
        """
        初始化MinIO客户端
        
        Args:
            endpoint: MinIO服务地址
            access_key: 访问密钥
            secret_key: 秘密密钥
            secure: 是否使用HTTPS
            bucket: 默认存储桶
            region: 区域
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.bucket = bucket
        self.region = region
        
        # 尝试导入minio库
        self._minio_available = False
        try:
            from minio import Minio
            from minio.error import S3Error
            self._minio = Minio
            self._s3_error = S3Error
            self._minio_available = True
            self._client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
        except ImportError:
            # 使用本地存储作为后备
            self._minio = None
            self._client = LocalStorageClient()
    
    def upload_file(
        self,
        local_path: str,
        object_name: str,
        metadata: Optional[Dict[str, str]] = None,
        bucket: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        上传本地文件
        
        Args:
            local_path: 本地文件路径
            object_name: 对象名称
            metadata: 元数据字典
            bucket: 存储桶（可选）
            
        Returns:
            上传结果
        """
        if self._minio_available:
            try:
                result = self._client.fput_object(
                    bucket or self.bucket,
                    object_name,
                    local_path,
                    metadata=metadata
                )
                return {
                    'object_name': object_name,
                    'etag': result.etag,
                    'version_id': getattr(result, 'version_id', None),
                    'metadata': metadata or {}
                }
            except Exception as e:
                raise ConnectionError(f"Upload failed: {e}")
        else:
            return self._client.upload_file(local_path, object_name, metadata)
    
    def upload_data(
        self,
        data: bytes,
        object_name: str,
        metadata: Optional[Dict[str, str]] = None,
        bucket: Optional[str] = None,
        content_type: str = 'application/octet-stream'
    ) -> Dict[str, Any]:
        """
        上传字节数据
        
        Args:
            data: 字节数据
            object_name: 对象名称
            metadata: 元数据
            bucket: 存储桶
            content_type: 内容类型
            
        Returns:
            上传结果
        """
        if self._minio_available:
            from io import BytesIO
            try:
                result = self._client.put_object(
                    bucket or self.bucket,
                    object_name,
                    BytesIO(data),
                    length=len(data),
                    metadata=metadata,
                    content_type=content_type
                )
                return {
                    'object_name': object_name,
                    'etag': result.etag,
                    'size': len(data),
                    'metadata': metadata or {}
                }
            except Exception as e:
                raise ConnectionError(f"Upload failed: {e}")
        else:
            return self._client.upload_data(data, object_name, metadata)
    
    def download_file(
        self,
        object_name: str,
        local_path: str,
        bucket: Optional[str] = None
    ) -> str:
        """
        下载文件到本地
        
        Args:
            object_name: 对象名称
            local_path: 本地目标路径
            bucket: 存储桶
            
        Returns:
            下载后的文件路径
        """
        if self._minio_available:
            try:
                self._client.fget_object(
                    bucket or self.bucket,
                    object_name,
                    local_path
                )
                return local_path
            except Exception as e:
                raise ConnectionError(f"Download failed: {e}")
        else:
            return self._client.download_file(object_name, local_path)
    
    def download_data(self, object_name: str, bucket: Optional[str] = None) -> bytes:
        """
        下载数据
        
        Args:
            object_name: 对象名称
            bucket: 存储桶
            
        Returns:
            字节数据
        """
        if self._minio_available:
            try:
                response = self._client.get_object(
                    bucket or self.bucket,
                    object_name
                )
                data = response.read()
                response.close()
                response.release_conn()
                return data
            except Exception as e:
                raise ConnectionError(f"Download failed: {e}")
        else:
            return self._client.download_data(object_name)
    
    def delete(self, object_name: str, bucket: Optional[str] = None) -> bool:
        """
        删除对象
        
        Args:
            object_name: 对象名称
            bucket: 存储桶
            
        Returns:
            是否成功
        """
        if self._minio_available:
            try:
                self._client.remove_object(bucket or self.bucket, object_name)
                return True
            except Exception:
                return False
        else:
            return self._client.delete(object_name)
    
    def delete_multiple(
        self,
        object_names: List[str],
        bucket: Optional[str] = None
    ) -> bool:
        """批量删除"""
        if self._minio_available:
            try:
                for name in object_names:
                    self._client.remove_object(bucket or self.bucket, name)
                return True
            except Exception:
                return False
        else:
            for name in object_names:
                self._client.delete(name)
            return True
    
    def exists(self, object_name: str, bucket: Optional[str] = None) -> bool:
        """检查对象是否存在"""
        if self._minio_available:
            return self._client.stat_object(
                bucket or self.bucket,
                object_name
            ) is not None
        else:
            return self._client.exists(object_name)
    
    def list_objects(
        self,
        prefix: str = '',
        max_keys: int = 1000,
        bucket: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出对象
        
        Args:
            prefix: 前缀过滤
            max_keys: 最大返回数量
            bucket: 存储桶
            
        Returns:
            对象列表
        """
        if self._minio_available:
            try:
                objects = self._client.list_objects(
                    bucket or self.bucket,
                    prefix=prefix,
                    recursive=True
                )
                
                results = []
                for obj in objects:
                    results.append({
                        'object_name': obj.object_name,
                        'size': obj.size,
                        'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                        'etag': obj.etag,
                        'metadata': obj.metadata or {}
                    })
                    
                    if len(results) >= max_keys:
                        break
                
                return results
            except Exception as e:
                raise ConnectionError(f"List failed: {e}")
        else:
            return self._client.list_objects(prefix, max_keys)
    
    def get_metadata(self, object_name: str, bucket: Optional[str] = None) -> Dict[str, Any]:
        """
        获取对象元数据
        
        Args:
            object_name: 对象名称
            bucket: 存储桶
            
        Returns:
            元数据
        """
        if self._minio_available:
            try:
                stat = self._client.stat_object(bucket or self.bucket, object_name)
                return {
                    'size': stat.size,
                    'last_modified': stat.last_modified.isoformat() if stat.last_modified else None,
                    'metadata': stat.metadata or {},
                    'etag': stat.etag,
                    'content_type': stat.content_type
                }
            except Exception as e:
                raise ConnectionError(f"Metadata failed: {e}")
        else:
            return self._client.get_metadata(object_name)
    
    def presigned_get_object(
        self,
        object_name: str,
        expires: int = 3600,
        bucket: Optional[str] = None
    ) -> str:
        """
        生成预签名下载URL
        
        Args:
            object_name: 对象名称
            expires: 过期时间（秒）
            bucket: 存储桶
            
        Returns:
            预签名URL
        """
        if self._minio_available:
            try:
                return self._client.presigned_get_object(
                    bucket or self.bucket,
                    object_name,
                    expires=timedelta(seconds=expires)
                )
            except Exception as e:
                raise ConnectionError(f"Presigned URL failed: {e}")
        else:
            return f"file://{self._client.base_path}/{object_name}"
    
    def presigned_put_object(
        self,
        object_name: str,
        expires: int = 3600,
        bucket: Optional[str] = None
    ) -> str:
        """生成预签名上传URL"""
        if self._minio_available:
            try:
                return self._client.presigned_put_object(
                    bucket or self.bucket,
                    object_name,
                    expires=timedelta(seconds=expires)
                )
            except Exception as e:
                raise ConnectionError(f"Presigned URL failed: {e}")
        else:
            return f"file://{self._client.base_path}/{object_name}"
    
    def create_bucket(self, bucket: Optional[str] = None) -> bool:
        """创建存储桶"""
        if self._minio_available:
            try:
                if not self._client.bucket_exists(bucket or self.bucket):
                    self._client.make_bucket(bucket or self.bucket)
                return True
            except Exception:
                return False
        return True
    
    def list_buckets(self) -> List[Dict[str, Any]]:
        """列出所有存储桶"""
        if self._minio_available:
            try:
                buckets = self._client.list_buckets()
                return [
                    {
                        'name': b.name,
                        'creation_date': b.creation_date.isoformat() if b.creation_date else None
                    }
                    for b in buckets
                ]
            except Exception:
                return []
        else:
            return [{'name': 'default', 'creation_date': None}]
    
    def health_check(self) -> bool:
        """健康检查"""
        if self._minio_available:
            try:
                self._client.list_buckets()
                return True
            except Exception:
                return False
        else:
            return self._client.health_check()
    
    def copy_object(
        self,
        source_object: str,
        dest_object: str,
        source_bucket: Optional[str] = None,
        dest_bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """复制对象"""
        if self._minio_available:
            try:
                result = self._client.copy_object(
                    dest_bucket or self.bucket,
                    dest_object,
                    f"/{source_bucket or self.bucket}/{source_object}",
                    metadata=metadata
                )
                return {
                    'etag': result.etag,
                    'object_name': dest_object
                }
            except Exception as e:
                raise ConnectionError(f"Copy failed: {e}")
        else:
            # 本地存储复制
            data = self._client.download_data(source_object)
            return self._client.upload_data(data, dest_object, metadata)
    
    def close(self):
        """关闭连接"""
        pass


if __name__ == '__main__':
    import tempfile
    
    # 配置参数
    config = {
        'endpoint': 'localhost:9000',
        'access_key': 'minioadmin',
        'secret_key': 'minioadmin',
        'secure': False,
        'bucket': 'itops'
    }
    
    # 创建客户端（fallback到本地存储）
    client = MinIOClient(**config)
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('Hello, MinIO! This is a test file.')
        temp_path = f.name
    
    try:
        # 上传文件
        result = client.upload_file(
            temp_path,
            'test/sample.txt',
            metadata={'description': 'test file', 'type': 'sample'}
        )
        print(f"Upload result: {result}")
        
        # 下载数据
        data = client.download_data('test/sample.txt')
        print(f"Downloaded: {data.decode()}")
        
        # 获取元数据
        meta = client.get_metadata('test/sample.txt')
        print(f"Metadata: {meta}")
        
        # 列出对象
        objects = client.list_objects('test/')
        print(f"Objects: {[o['object_name'] for o in objects]}")
        
        # 生成预签名URL
        url = client.presigned_get_object('test/sample.txt', expires=3600)
        print(f"Presigned URL: {url}")
        
        # 删除对象
        client.delete('test/sample.txt')
        print("Deleted successfully")
        
        # 健康检查
        print(f"Health check: {client.health_check()}")
        
    finally:
        os.unlink(temp_path)
        client.close()
