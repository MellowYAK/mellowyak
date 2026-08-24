import neutral from "../../../assets/mascot/poses/yak-neutral.png";
import wave from "../../../assets/mascot/poses/yak-wave.png";
import thinking from "../../../assets/mascot/poses/yak-thinking.png";
import peekLaptop from "../../../assets/mascot/poses/yak-peek-laptop.png";
import winkThumbsup from "../../../assets/mascot/poses/yak-wink-thumbsup.png";
import warningStop from "../../../assets/mascot/poses/yak-warning-stop.png";
import teachingMap from "../../../assets/mascot/poses/yak-teaching-map.png";
import securityShield from "../../../assets/mascot/poses/yak-security-shield.png";
import workingLaptop from "../../../assets/mascot/poses/yak-working-laptop.png";
import searchInspect from "../../../assets/mascot/poses/yak-search-inspect.png";
import alertPoint from "../../../assets/mascot/poses/yak-alert-point.png";
import successCheck from "../../../assets/mascot/poses/yak-success-check.png";
import confused from "../../../assets/mascot/poses/yak-confused.png";
import sleeping from "../../../assets/mascot/poses/yak-sleeping.png";
import celebrate from "../../../assets/mascot/poses/yak-celebrate.png";
import relaxedChair from "../../../assets/mascot/poses/yak-relaxed-chair.png";
import type { TranslationKey } from "./i18n";

export type MascotId =
  | "yak-neutral"
  | "yak-wave"
  | "yak-thinking"
  | "yak-peek-laptop"
  | "yak-wink-thumbsup"
  | "yak-warning-stop"
  | "yak-teaching-map"
  | "yak-security-shield"
  | "yak-working-laptop"
  | "yak-search-inspect"
  | "yak-alert-point"
  | "yak-success-check"
  | "yak-confused"
  | "yak-sleeping"
  | "yak-celebrate"
  | "yak-relaxed-chair";

export const mascotAssets: Record<MascotId, { src: string; altKey: TranslationKey }> = {
  "yak-neutral": { src: neutral, altKey: "mascot.meaning.neutral" },
  "yak-wave": { src: wave, altKey: "mascot.meaning.wave" },
  "yak-thinking": { src: thinking, altKey: "mascot.meaning.thinking" },
  "yak-peek-laptop": { src: peekLaptop, altKey: "mascot.meaning.peekLaptop" },
  "yak-wink-thumbsup": { src: winkThumbsup, altKey: "mascot.meaning.winkThumbsup" },
  "yak-warning-stop": { src: warningStop, altKey: "mascot.meaning.warningStop" },
  "yak-teaching-map": { src: teachingMap, altKey: "mascot.meaning.teachingMap" },
  "yak-security-shield": { src: securityShield, altKey: "mascot.meaning.securityShield" },
  "yak-working-laptop": { src: workingLaptop, altKey: "mascot.meaning.workingLaptop" },
  "yak-search-inspect": { src: searchInspect, altKey: "mascot.meaning.searchInspect" },
  "yak-alert-point": { src: alertPoint, altKey: "mascot.meaning.alertPoint" },
  "yak-success-check": { src: successCheck, altKey: "mascot.meaning.successCheck" },
  "yak-confused": { src: confused, altKey: "mascot.meaning.confused" },
  "yak-sleeping": { src: sleeping, altKey: "mascot.meaning.sleeping" },
  "yak-celebrate": { src: celebrate, altKey: "mascot.meaning.celebrate" },
  "yak-relaxed-chair": { src: relaxedChair, altKey: "mascot.meaning.relaxedChair" },
};
