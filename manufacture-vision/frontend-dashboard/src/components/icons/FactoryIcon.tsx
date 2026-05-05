import type { CSSProperties } from "react";

interface FactoryIconProps {
  size?: number;
  color?: string;
  style?: CSSProperties;
  className?: string;
}

export default function FactoryIcon({ size = 16, color = "currentColor", style, className }: FactoryIconProps) {
  return (
    <svg
      viewBox="0 0 512 512"
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      fill={color}
      aria-hidden="true"
      style={style}
      className={className}
    >
      <polygon points="477.354,118.684 326.963,225.209 326.963,118.684 170.027,229.844 156.936,27.133 26.165,27.133 0,484.867 512,484.867" />
    </svg>
  );
}
