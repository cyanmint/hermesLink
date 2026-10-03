/* HermesLink AI-generated glue code; created by cyanmint's coding agent.
 * AI-generated content has no copyright holder and is not subject to copyright. */
#include <asm/fcntl.h>
#include <linux/dcache.h>
#include <linux/fs.h>
#include <linux/fs_context.h>
#include <linux/init.h>
#include <linux/limits.h>
#include <linux/mount.h>
#include <linux/pagemap.h>
#include <linux/statfs.h>
#include <linux/uio.h>
#include <user/fs.h>

#include "../fs/hostfs/hostfs.h"

struct documentsfs_super {
  int root_fd;
  umode_t mask;
};

struct documentsfs_context {
  char *path;
  umode_t mask;
  bool mask_set;
};

#define DOCUMENTSFS_INODE_FD(inode) ((int)(uintptr_t)(inode)->i_private)
#define DOCUMENTSFS_FILE_FD(file) ((int)(long)(file)->private_data)
#define DOCUMENTSFS_MAGIC 0x646f6373

static const struct inode_operations documentsfs_dir_iops;
static const struct inode_operations documentsfs_file_iops;
static const struct file_operations documentsfs_file_fops;
static const struct file_operations documentsfs_dir_fops;

static const struct dentry_operations documentsfs_dentry_ops = {
  .d_delete = always_delete_dentry,
};

static umode_t documentsfs_mode(const struct documentsfs_super *info,
                                unsigned int host_mode) {
  if (S_ISDIR(host_mode))
    return S_IFDIR | (0777 & ~info->mask);
  if (S_ISREG(host_mode))
    return S_IFREG | (0666 & ~info->mask);
  return 0;
}

static int documentsfs_read_inode(struct inode *inode) {
  struct documentsfs_super *info = inode->i_sb->s_fs_info;
  struct hostfs_stat stat;
  int error = stat_file(NULL, &stat, DOCUMENTSFS_INODE_FD(inode));
  if (error < 0)
    return error;

  inode->i_ino = stat.ino != 0 ? stat.ino : 1;
  inode->i_mode = documentsfs_mode(info, stat.mode);
  if (inode->i_mode == 0)
    return -EOPNOTSUPP;
  i_uid_write(inode, 0);
  i_gid_write(inode, 0);
  set_nlink(inode, stat.nlink);
  inode->i_size = stat.size;
  inode->i_blocks = stat.blocks;
  inode->i_atime.tv_sec = stat.atime.tv_sec;
  inode->i_atime.tv_nsec = stat.atime.tv_nsec;
  inode->i_ctime.tv_sec = stat.ctime.tv_sec;
  inode->i_ctime.tv_nsec = stat.ctime.tv_nsec;
  inode->i_mtime.tv_sec = stat.mtime.tv_sec;
  inode->i_mtime.tv_nsec = stat.mtime.tv_nsec;

  if (S_ISDIR(inode->i_mode)) {
    inode->i_op = &documentsfs_dir_iops;
    inode->i_fop = &documentsfs_dir_fops;
  } else {
    inode->i_op = &documentsfs_file_iops;
    inode->i_fop = &documentsfs_file_fops;
  }
  return 0;
}

static int documentsfs_open_child(struct inode *directory,
                                  struct dentry *dentry) {
  return host_openat(DOCUMENTSFS_INODE_FD(directory),
                     dentry->d_name.name, O_RDONLY | O_NOFOLLOW, 0);
}

static struct dentry *documentsfs_lookup(struct inode *directory,
                                        struct dentry *dentry,
                                        unsigned int flags) {
  int fd = documentsfs_open_child(directory, dentry);
  if (fd == -ELOOP)
    return ERR_PTR(fd);
  if (fd == -ENOENT) {
    d_add(dentry, NULL);
    return NULL;
  }
  if (fd < 0)
    return ERR_PTR(fd);

  struct inode *inode = new_inode(directory->i_sb);
  if (inode == NULL) {
    host_close(fd);
    return ERR_PTR(-ENOMEM);
  }
  inode->i_private = (void *)(uintptr_t)fd;
  int error = documentsfs_read_inode(inode);
  if (error < 0) {
    host_close(fd);
    inode->i_private = (void *)(uintptr_t)-1;
    iput(inode);
    return ERR_PTR(error);
  }
  return d_splice_alias(inode, dentry);
}

static int documentsfs_open(struct inode *inode, struct file *file) {
  if (S_ISDIR(inode->i_mode)) {
    int error = host_dup_opendir(DOCUMENTSFS_INODE_FD(inode),
                                 &file->private_data);
    return error;
  }

  struct dentry *dentry = file->f_path.dentry;
  int fd = host_openat(DOCUMENTSFS_INODE_FD(d_inode(dentry->d_parent)),
                       dentry->d_name.name,
                       file->f_flags | O_NOFOLLOW, 0666);
  if (fd == -ELOOP)
    return -ENOENT;
  if (fd < 0)
    return fd;
  file->private_data = (void *)(long)fd;
  return 0;
}

static int documentsfs_create_node(struct user_namespace *mnt_userns,
                                   struct inode *directory,
                                   struct dentry *dentry,
                                   umode_t mode, int fd) {
  struct inode *inode = new_inode(directory->i_sb);
  if (inode == NULL) {
    if (fd >= 0)
      host_close(fd);
    return -ENOMEM;
  }
  inode_init_owner(mnt_userns, inode, directory, mode);
  inode->i_private = (void *)(uintptr_t)fd;
  int error = documentsfs_read_inode(inode);
  if (error < 0) {
    if (fd >= 0)
      host_close(fd);
    inode->i_private = (void *)(uintptr_t)-1;
    iput(inode);
    return error;
  }
  d_instantiate(dentry, inode);
  return 0;
}

static int documentsfs_create(struct user_namespace *mnt_userns,
                              struct inode *directory,
                              struct dentry *dentry, umode_t mode,
                              bool excl) {
  int fd = host_openat(DOCUMENTSFS_INODE_FD(directory),
                       dentry->d_name.name,
                       O_CREAT | O_RDWR | O_NOFOLLOW | (excl ? O_EXCL : 0),
                       0666);
  if (fd < 0)
    return fd;
  int error = documentsfs_create_node(mnt_userns, directory, dentry,
                                      S_IFREG | mode, fd);
  if (error < 0)
    host_unlinkat(DOCUMENTSFS_INODE_FD(directory), dentry->d_name.name);
  return error;
}

static int documentsfs_mkdir(struct user_namespace *mnt_userns,
                             struct inode *directory,
                             struct dentry *dentry, umode_t mode) {
  int error = host_mkdirat(DOCUMENTSFS_INODE_FD(directory),
                           dentry->d_name.name, 0777);
  if (error < 0)
    return error;
  int fd = documentsfs_open_child(directory, dentry);
  if (fd < 0) {
    host_rmdirat(DOCUMENTSFS_INODE_FD(directory), dentry->d_name.name);
    return fd;
  }
  error = documentsfs_create_node(mnt_userns, directory, dentry,
                                  S_IFDIR | mode, fd);
  if (error < 0)
    host_rmdirat(DOCUMENTSFS_INODE_FD(directory), dentry->d_name.name);
  return error;
}

static int documentsfs_unlink(struct inode *directory,
                              struct dentry *dentry) {
  return host_unlinkat(DOCUMENTSFS_INODE_FD(directory),
                       dentry->d_name.name);
}

static int documentsfs_rmdir(struct inode *directory,
                             struct dentry *dentry) {
  return host_rmdirat(DOCUMENTSFS_INODE_FD(directory),
                      dentry->d_name.name);
}

static int documentsfs_rename(struct user_namespace *mnt_userns,
                              struct inode *from_directory,
                              struct dentry *from_dentry,
                              struct inode *to_directory,
                              struct dentry *to_dentry,
                              unsigned int flags) {
  if (flags != 0)
    return -EINVAL;
  return host_renameat(DOCUMENTSFS_INODE_FD(from_directory),
                       from_dentry->d_name.name,
                       DOCUMENTSFS_INODE_FD(to_directory),
                       to_dentry->d_name.name);
}

static int documentsfs_setattr(struct user_namespace *mnt_userns,
                              struct dentry *dentry,
                              struct iattr *attributes) {
  if (attributes->ia_valid & ~(ATTR_SIZE | ATTR_CTIME))
    return -EOPNOTSUPP;
  int error = setattr_prepare(mnt_userns, dentry, attributes);
  if (error < 0)
    return error;
  if (attributes->ia_valid & ATTR_SIZE) {
    struct inode *inode = d_inode(dentry);
    struct dentry *parent = dentry->d_parent;
    int fd = host_openat(DOCUMENTSFS_INODE_FD(d_inode(parent)),
                        dentry->d_name.name, O_WRONLY | O_NOFOLLOW, 0);
    if (fd < 0)
      return fd;
    error = host_ftruncate(fd, attributes->ia_size);
    host_close(fd);
    if (error < 0)
      return error;
    truncate_setsize(inode, attributes->ia_size);
  }
  return 0;
}

static const struct inode_operations documentsfs_file_iops = {
  .setattr = documentsfs_setattr,
};

static const struct inode_operations documentsfs_dir_iops = {
  .lookup = documentsfs_lookup,
  .create = documentsfs_create,
  .mkdir = documentsfs_mkdir,
  .unlink = documentsfs_unlink,
  .rmdir = documentsfs_rmdir,
  .rename = documentsfs_rename,
  .setattr = documentsfs_setattr,
};

static ssize_t documentsfs_read_iter(struct kiocb *iocb,
                                     struct iov_iter *to) {
  char *buffer = kmalloc(PAGE_SIZE, GFP_KERNEL);
  if (buffer == NULL)
    return -ENOMEM;
  ssize_t total = 0;
  while (iov_iter_count(to) > 0) {
    size_t count = min_t(size_t, iov_iter_count(to), PAGE_SIZE);
    ssize_t read_count = host_pread(DOCUMENTSFS_FILE_FD(iocb->ki_filp),
                                    buffer, count, iocb->ki_pos);
    if (read_count <= 0) {
      if (read_count < 0 && total == 0)
        total = read_count;
      break;
    }
    size_t copied = copy_to_iter(buffer, read_count, to);
    iocb->ki_pos += copied;
    total += copied;
    if (copied != read_count)
      break;
  }
  kfree(buffer);
  return total;
}

static ssize_t documentsfs_write_iter(struct kiocb *iocb,
                                      struct iov_iter *from) {
  char *buffer = kmalloc(PAGE_SIZE, GFP_KERNEL);
  if (buffer == NULL)
    return -ENOMEM;
  ssize_t total = 0;
  while (iov_iter_count(from) > 0) {
    size_t count = min_t(size_t, iov_iter_count(from), PAGE_SIZE);
    size_t copied = copy_from_iter(buffer, count, from);
    if (copied == 0)
      break;
    ssize_t written = host_pwrite(DOCUMENTSFS_FILE_FD(iocb->ki_filp),
                                  buffer, copied, iocb->ki_pos);
    if (written < 0) {
      if (total == 0)
        total = written;
      break;
    }
    iocb->ki_pos += written;
    total += written;
    if (iocb->ki_pos > i_size_read(iocb->ki_filp->f_inode))
      i_size_write(iocb->ki_filp->f_inode, iocb->ki_pos);
    if ((size_t)written != copied)
      break;
  }
  kfree(buffer);
  return total;
}

static int documentsfs_release(struct inode *inode, struct file *file) {
  if (S_ISDIR(inode->i_mode))
    return host_closedir(file->private_data);
  return host_close(DOCUMENTSFS_FILE_FD(file));
}

static int documentsfs_fsync(struct file *file, loff_t start, loff_t end,
                             int datasync) {
  return host_fsync(DOCUMENTSFS_FILE_FD(file), datasync);
}

static const struct file_operations documentsfs_file_fops = {
  .open = documentsfs_open,
  .llseek = generic_file_llseek,
  .read_iter = documentsfs_read_iter,
  .write_iter = documentsfs_write_iter,
  .release = documentsfs_release,
  .fsync = documentsfs_fsync,
};

static int documentsfs_iterate(struct file *file, struct dir_context *ctx) {
  void *directory = file->private_data;
  int error = ctx->pos == 0
      ? host_rewinddir(directory)
      : host_seekdir(directory, ctx->pos - 1);
  if (error < 0)
    return error;

  struct host_dirent entry;
  for (;;) {
    error = host_readdir(directory, &entry);
    if (error <= 0)
      return error;
    long position = host_telldir(directory);
    if (entry.type == DT_LNK) {
      ctx->pos = position + 1;
      continue;
    }
    ino_t inode = entry.ino != 0 ? entry.ino : 1;
    if (!dir_emit(ctx, entry.name, strlen(entry.name), inode, entry.type))
      return 0;
    ctx->pos = position + 1;
  }
}

static int documentsfs_dir_release(struct inode *inode, struct file *file) {
  return documentsfs_release(inode, file);
}

static const struct file_operations documentsfs_dir_fops = {
  .open = documentsfs_open,
  .iterate = documentsfs_iterate,
  .release = documentsfs_dir_release,
  .llseek = generic_file_llseek,
};

static void documentsfs_evict_inode(struct inode *inode) {
  struct documentsfs_super *info = inode->i_sb->s_fs_info;
  int fd = DOCUMENTSFS_INODE_FD(inode);
  if (fd >= 0 && fd != info->root_fd)
    host_close(fd);
  inode->i_private = (void *)(uintptr_t)-1;
  clear_inode(inode);
}

static int documentsfs_statfs(struct dentry *dentry,
                              struct kstatfs *stat) {
  struct documentsfs_super *info = dentry->d_sb->s_fs_info;
  struct host_statfs host;
  int error = host_fstatfs(info->root_fd, &host);
  if (error < 0)
    return error;
  stat->f_type = DOCUMENTSFS_MAGIC;
  stat->f_bsize = host.bsize;
  stat->f_frsize = host.frsize;
  stat->f_blocks = host.blocks;
  stat->f_bfree = host.bfree;
  stat->f_bavail = host.bavail;
  stat->f_files = host.files;
  stat->f_ffree = host.ffree;
  stat->f_fsid = u64_to_fsid(host.fsid);
  stat->f_namelen = host.namemax;
  return 0;
}

static const struct super_operations documentsfs_super_ops = {
  .drop_inode = generic_delete_inode,
  .evict_inode = documentsfs_evict_inode,
  .statfs = documentsfs_statfs,
};

static int documentsfs_fill_super(struct super_block *sb,
                                  struct fs_context *fc) {
  int error = super_setup_bdi(sb);
  if (error < 0)
    return error;
  struct inode *root = new_inode(sb);
  if (root == NULL)
    return -ENOMEM;
  struct documentsfs_super *info = sb->s_fs_info;
  root->i_private = (void *)(uintptr_t)info->root_fd;
  error = documentsfs_read_inode(root);
  if (error < 0) {
    iput(root);
    return error;
  }
  sb->s_op = &documentsfs_super_ops;
  sb->s_d_op = &documentsfs_dentry_ops;
  sb->s_root = d_make_root(root);
  return sb->s_root != NULL ? 0 : -ENOMEM;
}

static int documentsfs_parse_param(struct fs_context *fc,
                                   struct fs_parameter *param) {
  struct documentsfs_context *ctx = fc->fs_private;
  if (strcmp(param->key, "source") == 0) {
    char *path = kstrdup(param->string, GFP_KERNEL);
    if (path == NULL)
      return -ENOMEM;
    kfree(ctx->path);
    ctx->path = path;
    return 0;
  }
  if (strcmp(param->key, "mask") == 0) {
    unsigned int mask;
    if (param->type != fs_value_is_string ||
        kstrtouint(param->string, 8, &mask) != 0 || mask > 0777)
      return -EINVAL;
    ctx->mask = mask;
    ctx->mask_set = true;
    return 0;
  }
  return -EINVAL;
}

static void documentsfs_fc_free(struct fs_context *fc) {
  struct documentsfs_context *ctx = fc->fs_private;
  if (ctx != NULL) {
    kfree(ctx->path);
    kfree(ctx);
  }
}

static int documentsfs_get_tree(struct fs_context *fc) {
  struct documentsfs_context *ctx = fc->fs_private;
  if (ctx->path == NULL || ctx->path[0] != '/')
    return -EINVAL;
  struct documentsfs_super *info = kzalloc(sizeof(*info), GFP_KERNEL);
  if (info == NULL)
    return -ENOMEM;
  info->mask = ctx->mask_set ? ctx->mask : 0022;
  info->root_fd = host_open(ctx->path, O_RDONLY);
  if (info->root_fd < 0) {
    int error = info->root_fd;
    kfree(info);
    return error;
  }
  struct hostfs_stat root_stat;
  int error = stat_file(NULL, &root_stat, info->root_fd);
  if (error < 0 || !S_ISDIR(root_stat.mode)) {
    host_close(info->root_fd);
    kfree(info);
    return error < 0 ? error : -ENOTDIR;
  }
  fc->s_fs_info = info;
  error = vfs_get_super(fc, vfs_get_independent_super,
                        documentsfs_fill_super);
  if (error < 0 && fc->s_fs_info == info) {
    fc->s_fs_info = NULL;
    host_close(info->root_fd);
    kfree(info);
  }
  return error;
}

static void documentsfs_apply_mask(struct super_block *sb, umode_t mask) {
  struct documentsfs_super *info = sb->s_fs_info;
  struct inode *inode;
  info->mask = mask;
  spin_lock(&sb->s_inode_list_lock);
  list_for_each_entry(inode, &sb->s_inodes, i_sb_list) {
    spin_lock(&inode->i_lock);
    inode->i_mode = documentsfs_mode(
        info, S_ISDIR(inode->i_mode) ? S_IFDIR : S_IFREG);
    spin_unlock(&inode->i_lock);
  }
  spin_unlock(&sb->s_inode_list_lock);
}

static int documentsfs_reconfigure(struct fs_context *fc) {
  struct documentsfs_context *ctx = fc->fs_private;
  if (ctx->mask_set)
    documentsfs_apply_mask(fc->root->d_sb, ctx->mask);
  return 0;
}

static struct fs_context_operations documentsfs_context_ops = {
  .parse_param = documentsfs_parse_param,
  .free = documentsfs_fc_free,
  .get_tree = documentsfs_get_tree,
  .reconfigure = documentsfs_reconfigure,
};

static int documentsfs_init_fs_context(struct fs_context *fc) {
  fc->ops = &documentsfs_context_ops;
  fc->fs_private = kzalloc(sizeof(struct documentsfs_context), GFP_KERNEL);
  return fc->fs_private != NULL ? 0 : -ENOMEM;
}

static void documentsfs_kill_sb(struct super_block *sb) {
  struct documentsfs_super *info = sb->s_fs_info;
  kill_anon_super(sb);
  if (info != NULL) {
    host_close(info->root_fd);
    kfree(info);
  }
}

static struct file_system_type documentsfs_type = {
  .name = "documentsfs",
  .init_fs_context = documentsfs_init_fs_context,
  .kill_sb = documentsfs_kill_sb,
};

static int __init documentsfs_init(void) {
  return register_filesystem(&documentsfs_type);
}
fs_initcall(documentsfs_init);
