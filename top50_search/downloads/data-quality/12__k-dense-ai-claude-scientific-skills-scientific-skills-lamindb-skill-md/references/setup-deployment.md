LaminDB Setup & Deployment

This document covers installation, configuration, instance management, storage options, and deployment strategies for LaminDB.

Installation

Basic Installation

# Install LaminDB
pip install lamindb

# Or with pip3
pip3 install lamindb

Installation with Extras

Install optional dependencies for specific functionality:

# Google Cloud Platform support
pip install 'lamindb[gcp]'

# Flow cytometry formats
pip install 'lamindb[fcs]'

# Array storage and streaming (Zarr support)
pip install 'lamindb[zarr]'

# AWS S3 support (usually included by default)
pip install 'lamindb[aws]'

# Multiple extras
pip install 'lamindb[gcp,zarr,fcs]'

Module Plugins

# Biological ontologies (Bionty)
pip install bionty

# Wet lab functionality
pip install lamindb-wetlab

# Clinical data (OMOP CDM)
pip install lamindb-clinical

Verify Installation

import lamindb as ln
print(ln.__version__)

# Check available modules
import bionty as bt
print(bt.__version__)

Authentication

Creating an Account

Visit https://lamin.ai

Sign up for a free account

Navigate to account settings to generate an API key

Logging In

# Login with API key
lamin login

# You'll be prompted to enter your API key
# API key is stored locally at ~/.lamin/

Authentication Details

Data Privacy: LaminDB authentication only collects basic metadata (email, user information). Your actual data remains private and is not sent to LaminDB servers.

Local vs Cloud: Authentication is required even for local-only usage to enable collaboration features and instance management.

Instance Initialization

Local SQLite Instance

For local development and small datasets:

# Initialize in current directory
lamin init --storage ./mydata

# Initialize in specific directory
lamin init --storage /path/to/data

# Initialize with specific modules
lamin init --storage ./mydata --modules bionty

# Initialize with multiple modules
lamin init --storage ./mydata --modules bionty,wetlab

Cloud Storage with SQLite

Use cloud storage but local SQLite database:

# AWS S3
lamin init --storage s3://my-bucket/path

# Google Cloud Storage
lamin init --storage gs://my-bucket/path

# S3-compatible (MinIO, Cloudflare R2)
lamin init --storage 's3://bucket?endpoint_url=http://endpoint:9000'

Cloud Storage with PostgreSQL

For production deployments:

# S3 + PostgreSQL
lamin init --storage s3://my-bucket/path \
--db postgresql://user:password@hostname:5432/dbname \
--modules bionty

# GCS + PostgreSQL
lamin init --storage gs://my-bucket/path \
--db postgresql://user:password@hostname:5432/dbname \
--modules bionty

Instance Naming

# Specify instance name
lamin init --storage ./mydata --name my-project

# Default name uses directory name
lamin init --storage ./mydata  # Instance name: "mydata"

Connecting to Instances

Connect to Your Own Instance

# By name
lamin connect my-project

# By full path
lamin connect account_handle/my-project

Connect to Shared Instance

# Connect to someone else's instance
lamin connect other-user/their-project

# Requires appropriate permissions

Switching Between Instances

# List available instances
lamin info

# Switch instance
lamin connect another-instance

# Close current instance
lamin close

Storage Configuration

Local Storage

Advantages:

Fast access

No internet required

Simple setup

Setup:

lamin init --storage ./data

AWS S3 Storage

Advantages:

Scalable

Collaborative

Durable

Setup:

# Set credentials
export AWS_ACCESS_KEY_ID=your_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Initialize
lamin init --storage s3://my-bucket/project-data \
--db postgresql://user:pwd@host:5432/db

S3 Permissions Required:

{
"Version": "2012-10-17",
"Statement": [
{
"Effect": "Allow",
"Action": [
"s3:GetObject",
"s3:PutObject",
"s3:DeleteObject",
"s3:ListBucket"
],
"Resource": [
"arn:aws:s3:::my-bucket/*",
"arn:aws:s3:::my-bucket"
]
}
]
}

Google Cloud Storage

Setup:

# Authenticate
gcloud auth application-default login

# Or use service account
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Initialize
lamin init --storage gs://my-bucket/project-data \
--db postgresql://user:pwd@host:5432/db

S3-Compatible Storage

For MinIO, Cloudflare R2, or other S3-compatible services:

# MinIO example
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin

lamin init --storage 's3://my-bucket?endpoint_url=http://minio.example.com:9000'

# Cloudflare R2 example
export AWS_ACCESS_KEY_ID=your_r2_access_key
export AWS_SECRET_ACCESS_KEY=your_r2_secret_key

lamin init --storage 's3://bucket?endpoint_url=https://account-id.r2.cloudflarestorage.com'

Database Configuration

SQLite (Default)

Advantages:

No separate database server

Simple setup

Good for development

Limitations:

Not suitable for concurrent writes

Limited scalability

Setup:

# SQLite is default
lamin init --storage ./data
# Database stored at ./data/.lamindb/

PostgreSQL

Advantages:

Production-ready

Concurrent access

Better performance at scale

Setup:

# Full connection string
lamin init --storage s3://bucket/path \
--db postgresql://username:password@hostname:5432/database

# With SSL
lamin init --storage s3://bucket/path \
--db "postgresql://user:pwd@host:5432/db?sslmode=require"

PostgreSQL Versions: Compatible with PostgreSQL 12+

Database Schema Management

# Check current schema version
lamin migrate check

# Upgrade schema
lamin migrate deploy

# View migration history
lamin migrate history

Cache Configuration

Cache Directory

LaminDB maintains a local cache for cloud files:

import lamindb as ln

# View cache location
print(ln.settings.cache_dir)

Configure Cache Location

# Set cache directory
lamin cache set /path/to/cache

# View current cache settings
lamin cache get

System-Wide Cache (Multi-User)

For shared systems with multiple users:

# Create system settings file
sudo mkdir -p /system/settings
sudo nano /system/settings/system.env

Add to system.env:

lamindb_cache_path=/shared/cache/lamindb

Ensure permissions:

sudo chmod 755 /shared/cache/lamindb
sudo chown -R shared-user:shared-group /shared/cache/lamindb

Cache Management

import lamindb as ln

# Clear cache for specific artifact
artifact = ln.Artifact.get(key="data.h5ad")
artifact.delete_cache()

# Check if artifact is cached
if artifact.is_cached():
print("Already cached")

# Manually clear entire cache
import shutil
shutil.rmtree(ln.settings.cache_dir)

Settings Management

View Current Settings

import lamindb as ln

# User settings
print(ln.setup.settings.user)
# User(handle='username', email='user@email.com', name='Full Name')

# Instance settings
print(ln.setup.settings.instance)
# Instance(name='my-project', storage='s3://bucket/path')

Configure Settings

# Set development directory for relative keys
lamin settings set dev-dir /path/to/project

# Configure git sync
lamin settings set sync-git-repo https://github.com/user/repo.git

# View all settings
lamin settings

Environment Variables

# Cache directory
export LAMIN_CACHE_DIR=/path/to/cache

# Settings directory
export LAMIN_SETTINGS_DIR=/path/to/settings

# Git sync
export LAMINDB_SYNC_GIT_REPO=https://github.com/user/repo.git

Instance Management

Viewing Instance Information

# Current instance info
lamin info

# List all instances
lamin ls

# View instance details
lamin instance details

Instance Collaboration

# Set instance visibility (requires LaminHub)
lamin instance set-visibility public
lamin instance set-visibility private

# Invite collaborators (requires LaminHub)
lamin instance invite user@email.com

Instance Migration

# Backup instance
lamin backup create

# Restore from backup
lamin backup restore backup_id

# Export instance metadata
lamin export instance-metadata.json

Deleting Instances

# Delete instance (preserves data, removes metadata)
lamin delete --force instance-name

# This only removes the LaminDB metadata
# Actual data in storage location remains

Production Deployment Patterns

Pattern 1: Local Development → Cloud Production

Development:

# Local development
lamin init --storage ./dev-data --modules bionty

Production:

# Cloud production
lamin init --storage s3://prod-bucket/data \
--db postgresql://user:pwd@db-host:5432/prod-db \
--modules bionty \
--name production

Migration: Export artifacts from dev, import to prod

# Export from dev
artifacts = ln.Artifact.filter().all()
for artifact in artifacts:
artifact.export("/tmp/export/")

# Switch to prod
lamin connect production

# Import to prod
for file in Path("/tmp/export/").glob("*"):
ln.Artifact(str(file), key=file.name).save()

Pattern 2: Multi-Region Deployment

Deploy instances in multiple regions for data sovereignty:

# US instance
lamin init --storage s3://us-bucket/data \
--db postgresql://user:pwd@us-db:5432/db \
--name us-production

# EU instance
lamin init --storage s3://eu-bucket/data \
--db postgresql://user:pwd@eu-db:5432/db \
--name eu-production

Pattern 3: Shared Storage, Personal Instances

Multiple users, shared data:

# Shared storage with user-specific DB
lamin init --storage s3://shared-bucket/data \
--db postgresql://user1:pwd@host:5432/user1_db \
--name user1-workspace

lamin init --storage s3://shared-bucket/data \
--db postgresql://user2:pwd@host:5432/user2_db \
--name user2-workspace

Performance Optimization

Database Performance

# Use connection pooling for PostgreSQL
# Configure in database server settings

# Optimize queries with indexes
# LaminDB creates indexes automatically for common queries

Storage Performance

# Use appropriate storage classes
# S3: STANDARD for frequent access, INTELLIGENT_TIERING for mixed access

# Configure multipart upload thresholds
export AWS_CLI_FILE_IO_BANDWIDTH=100MB

Cache Optimization

# Pre-cache frequently used artifacts
artifacts = ln.Artifact.filter(key__startswith="reference/")
for artifact in artifacts:
artifact.cache()  # Download to cache

# Use backed mode for large arrays
adata = artifact.backed()  # Don't load into memory

Security Best Practices

Credentials Management:

Use environment variables, not hardcoded credentials

Use IAM roles on AWS/GCP instead of access keys

Rotate credentials regularly

Access Control:

Use PostgreSQL for multi-user access control

Configure storage bucket policies

Enable audit logging

Network Security:

Use SSL/TLS for database connections

Use VPCs for cloud deployments

Restrict IP addresses when possible

Data Protection:

Enable encryption at rest (S3, GCS)

Use encryption in transit (HTTPS, SSL)

Implement backup strategies

Monitoring and Maintenance

Health Checks

import lamindb as ln

# Check database connection
try:
ln.Artifact.filter().count()
print("✓ Database connected")
except Exception as e:
print(f"✗ Database error: {e}")

# Check storage access
try:
test_artifact = ln.Artifact("test.txt", key="healthcheck.txt").save()
test_artifact.delete(permanent=True)
print("✓ Storage accessible")
except Exception as e:
print(f"✗ Storage error: {e}")

Logging

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# LaminDB operations will produce detailed logs

Backup Strategy

# Regular database backups (PostgreSQL)
pg_dump -h hostname -U username -d database > backup_$(date +%Y%m%d).sql

# Storage backups (S3 versioning)
aws s3api put-bucket-versioning \
--bucket my-bucket \
--versioning-configuration Status=Enabled

# Metadata export
lamin export metadata_backup.json

Troubleshooting

Common Issues

Issue: Cannot connect to instance

# Check instance exists
lamin ls

# Verify authentication
lamin login

# Re-connect
lamin connect instance-name

Issue: Storage permissions denied

# Check AWS credentials
aws s3 ls s3://your-bucket/

# Check GCS credentials
gsutil ls gs://your-bucket/

# Verify IAM permissions

Issue: Database connection error

# Test PostgreSQL connection
psql postgresql://user:pwd@host:5432/db

# Check database version compatibility
lamin migrate check

Issue: Cache full

# Clear cache
import lamindb as ln
import shutil
shutil.rmtree(ln.settings.cache_dir)

# Set larger cache location
lamin cache set /larger/disk/cache

Upgrade and Migration

Upgrading LaminDB

# Upgrade to latest version
pip install --upgrade lamindb

# Upgrade database schema
lamin migrate deploy

Schema Compatibility

Check the compatibility matrix to ensure your database schema version is compatible with your installed LaminDB version.

Breaking Changes

Major version upgrades may require migration:

# Check for breaking changes
lamin migrate check

# Review migration plan
lamin migrate plan

# Execute migration
lamin migrate deploy

Best Practices

Start local, scale cloud: Develop locally, deploy to cloud for production

Use PostgreSQL for production: SQLite is only for development

Configure appropriate cache: Size cache based on working set

Enable versioning: Use S3/GCS versioning for data protection

Monitor costs: Track storage and compute costs in cloud deployments

Document configuration: Keep infrastructure-as-code for reproducibility

Test backups: Regularly verify backup and restore procedures

Set up monitoring: Implement health checks and alerting

Use modules strategically: Only install needed plugins to reduce complexity

Plan for scale: Consider concurrent users and data growth