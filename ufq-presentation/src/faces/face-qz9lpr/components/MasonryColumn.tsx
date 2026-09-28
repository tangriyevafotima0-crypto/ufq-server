import React from "react";

type GalleryImage = { src: string };

export default function MasonryColumn({
  images,
  direction,
  duration,
}: {
  images: GalleryImage[];
  direction: "up" | "down";
  duration: number;
}) {
  // Duplicate the set so the loop is seamless (track is 200% tall).
  const loop = [...images, ...images];

  return (
    <div className="relative h-full flex-1 overflow-hidden">
      <div
        className={`flex flex-col gap-4 @xl:gap-6 will-change-transform ${
          direction === "up" ? "masonry-track-up" : "masonry-track-down"
        }`}
        style={{ animationDuration: `${duration}s` }}
      >
        {loop.map((img, i) => (
          <div
            key={i}
            className="w-full overflow-hidden shrink-0"
          >
            <img
              src={img.src}
              alt=""
              className="w-full h-auto object-cover block"
            />
          </div>
        ))}
      </div>
    </div>
  );
}

