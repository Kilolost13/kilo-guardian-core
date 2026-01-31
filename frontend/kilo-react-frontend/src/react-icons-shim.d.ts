// Temporary shim for react-icons typing issues
// This forces react-icons modules to `any` to avoid TS2786 errors during development.
// Remove after migrating to a toolchain that supports the latest types or when react-icons types are compatible.

declare module 'react-icons/*' {
  const _: any;
  export default _;
}

declare module 'react-icons/fa' {
  const _: any;
  export const FaMicrophone: any;
  export const FaMicrophoneSlash: any;
  export const FaStop: any;
  export const FaBrain: any;
  export const FaBell: any;
  export const FaChartLine: any;
  export const FaLightbulb: any;
  export const FaTrophy: any;
  export const FaSearch: any;
  export const FaPlus: any;
  export const FaBullseye: any;
  export const FaCalendarAlt: any;
  export const FaUser: any;
  export const FaCamera: any;
  export const FaVolumeUp: any;
  export const FaPaperclip: any;
  export const FaCog: any;
  export const FaFilter: any;
  export default _;
}