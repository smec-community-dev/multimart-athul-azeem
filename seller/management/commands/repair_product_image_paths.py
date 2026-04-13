import os
import re
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.template.defaultfilters import slugify

from seller.models import Product, ProductImage


class Command(BaseCommand):
    help = (
        "Auto-map product images from media/products using slug matching. "
        "Example: pixel-8-pro-main.jpg -> Product('Pixel 8 Pro') Main image."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to database.",
        )
        parser.add_argument(
            "--no-prune",
            action="store_true",
            help="Do not delete mismatched/duplicate ProductImage rows.",
        )
        parser.add_argument(
            "--keep-unmatched",
            action="store_true",
            help="Keep existing DB images for products with no matching files in media/products.",
        )

    @staticmethod
    def _normalized_stem(filename: str) -> str:
        stem, _ext = os.path.splitext(filename)
        # Django can append random suffixes on collisions, e.g. foo_x7Abc12.jpg
        stem = re.sub(r"_[A-Za-z0-9]{7}$", "", stem)
        return stem

    def _scan_media_products(self):
        products_dir = os.path.join(settings.MEDIA_ROOT, "products")
        if not os.path.isdir(products_dir):
            return {}, products_dir

        image_index = defaultdict(lambda: {"main": [], "gallery": []})
        for filename in os.listdir(products_dir):
            full_path = os.path.join(products_dir, filename)
            if not os.path.isfile(full_path):
                continue

            stem = self._normalized_stem(filename.lower())
            if stem.endswith("-main"):
                key = stem[: -len("-main")]
                image_index[key]["main"].append(filename)
            elif stem.endswith("-gallery"):
                key = stem[: -len("-gallery")]
                image_index[key]["gallery"].append(filename)

        for key in image_index:
            image_index[key]["main"].sort()
            image_index[key]["gallery"].sort()

        return image_index, products_dir

    def _resolve_files_for_product(self, product, image_index):
        name_slug = slugify(product.name)
        slug_field = (product.slug or "").strip().lower()
        keys = [name_slug]
        if slug_field and slug_field != name_slug:
            keys.append(slug_field)

        mains = []
        galleries = []
        for key in keys:
            if key in image_index:
                mains.extend(image_index[key]["main"])
                galleries.extend(image_index[key]["gallery"])

        # Preserve order + de-dupe
        mains = list(dict.fromkeys(mains))
        galleries = list(dict.fromkeys(galleries))

        return mains, galleries, keys

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        prune = not options["no_prune"]
        keep_unmatched = options["keep_unmatched"]
        image_index, products_dir = self._scan_media_products()

        if not os.path.isdir(products_dir):
            self.stdout.write(self.style.ERROR(f"Missing folder: {products_dir}"))
            return

        created = 0
        updated = 0
        deleted = 0
        skipped = 0
        cleaned_unmatched = 0
        unmatched_products = []

        queryset = Product.objects.all().prefetch_related("images")
        for product in queryset:
            mains, galleries, keys = self._resolve_files_for_product(product, image_index)
            if not mains and not galleries:
                unmatched_products.append(f"{product.id}:{product.name} ({', '.join(keys)})")
                skipped += 1
                if prune and not keep_unmatched:
                    existing_images = list(product.images.all())
                    if existing_images:
                        if not dry_run:
                            for img in existing_images:
                                img.delete()
                        cleaned_unmatched += len(existing_images)
                continue

            # Exact target set for this product.
            target_files = []
            main_file = mains[0] if mains else (galleries[0] if galleries else None)
            if main_file:
                target_files.append(main_file)
            if galleries:
                # If gallery fallback is promoted to Main, keep remaining as Gallery.
                target_files.extend([g for g in galleries if g != main_file])
            target_files = list(dict.fromkeys(target_files))
            target_paths = {f"products/{name}" for name in target_files}

            with transaction.atomic():
                existing_images = list(product.images.all())

                # Upsert main image
                if main_file:
                    main_path = f"products/{main_file}"
                    main_obj = next(
                        (img for img in existing_images if img.image and img.image.name == main_path),
                        None,
                    )
                    if main_obj:
                        if main_obj.image_type != "Main":
                            if not dry_run:
                                main_obj.image_type = "Main"
                                main_obj.save(update_fields=["image_type"])
                            updated += 1
                    else:
                        if not dry_run:
                            ProductImage.objects.create(
                                product=product,
                                image=main_path,
                                image_type="Main",
                            )
                        created += 1

                # Upsert gallery images
                for gallery_file in galleries:
                    if gallery_file == main_file:
                        continue
                    gallery_path = f"products/{gallery_file}"
                    gallery_obj = next(
                        (img for img in existing_images if img.image and img.image.name == gallery_path),
                        None,
                    )
                    if gallery_obj:
                        if gallery_obj.image_type != "Gallery":
                            if not dry_run:
                                gallery_obj.image_type = "Gallery"
                                gallery_obj.save(update_fields=["image_type"])
                            updated += 1
                    else:
                        if not dry_run:
                            ProductImage.objects.create(
                                product=product,
                                image=gallery_path,
                                image_type="Gallery",
                            )
                        created += 1

                if prune:
                    # Refresh current state if writes happened.
                    current = list(product.images.all()) if not dry_run else existing_images
                    seen_paths = set()
                    for img in current:
                        image_name = (img.image.name or "").strip() if img.image else ""
                        should_delete = (
                            not image_name
                            or image_name not in target_paths
                            or image_name in seen_paths
                        )
                        if should_delete:
                            if not dry_run:
                                img.delete()
                            deleted += 1
                        else:
                            seen_paths.add(image_name)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Mapped product #{product.id} '{product.name}' "
                    f"-> main={main_file or 'NONE'}, gallery={len(galleries)}"
                )
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Image mapping completed."))
        self.stdout.write(f"Dry run: {dry_run}")
        self.stdout.write(f"Created: {created}")
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Deleted: {deleted}")
        self.stdout.write(f"Deleted unmatched stale rows: {cleaned_unmatched}")
        self.stdout.write(f"Skipped (no matching files): {skipped}")

        if unmatched_products:
            self.stdout.write(self.style.WARNING("Unmatched products:"))
            for item in unmatched_products:
                self.stdout.write(f" - {item}")
