import os

import cloudinary
import cloudinary.uploader


def configured():
    if os.environ.get("CLOUDINARY_URL", "").strip():
        return True
    return all(os.environ.get(k, "").strip() for k in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"))


def setup():
    if os.environ.get("CLOUDINARY_URL", "").strip():
        cloudinary.config(secure=True)
        return
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"].strip(),
        api_key=os.environ["CLOUDINARY_API_KEY"].strip(),
        api_secret=os.environ["CLOUDINARY_API_SECRET"].strip(),
        secure=True,
    )


def folder():
    return os.environ.get("CLOUDINARY_FOLDER", "").strip()


def upload(data, filename):
    setup()
    result = cloudinary.uploader.upload(
        data,
        resource_type="auto",
        use_filename=True,
        unique_filename=True,
        overwrite=False,
        filename_override=filename,
        **({"folder": folder()} if folder() else {}),
    )
    return {"url": result["secure_url"], "public_id": result["public_id"], "resource_type": result.get("resource_type", "image")}


def remove(public_id, resource_type):
    setup()
    cloudinary.uploader.destroy(public_id, resource_type=resource_type or "image", invalidate=True)
