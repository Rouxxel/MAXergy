import logo64 from "@/assets/logo_64.png";
import logo128 from "@/assets/logo_128.png";
import logo512 from "@/assets/logo_512.png";

type LogoSize = 64 | 128 | 512;

interface LogoProps {
  size?: LogoSize;
  className?: string;
  alt?: string;
}

const logoMap = {
  64: logo64,
  128: logo128,
  512: logo512,
};

const sizeMap = {
  64: "h-16 w-16",
  128: "h-32 w-32",
  512: "h-64 w-64",
};

export function Logo({ size = 64, className, alt = "MAXergy Logo" }: LogoProps) {
  const logoSrc = logoMap[size];
  const sizeClass = sizeMap[size];

  return (
    <img
      src={logoSrc}
      alt={alt}
      className={`${sizeClass} ${className || ""}`}
    />
  );
}
