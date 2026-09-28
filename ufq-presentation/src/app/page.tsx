import React from "react";
import { NewSlidesLayout } from "@/components/entrypoint-layouts/new-slides-layout";
import { faces } from "@/faces.config.json";
import Face6ifrcsFace from "@/faces/face-6ifrcs/face.tsx";
import Facerjgam2Face from "@/faces/face-rjgam2/face.tsx";
import FacehodmbtFace from "@/faces/face-hodmbt/face.tsx";
import Facezeoka1Face from "@/faces/face-zeoka1/face.tsx";
import Facecdfv0fFace from "@/faces/face-cdfv0f/face.tsx";
import Face2o0r2aFace from "@/faces/face-2o0r2a/face.tsx";
import Faceo19ezsFace from "@/faces/face-o19ezs/face.tsx";
import Face5f2d3zFace from "@/faces/face-5f2d3z/face.tsx";
import Faceq1kgxgFace from "@/faces/face-q1kgxg/face.tsx";
import Facegjl8aaFace from "@/faces/face-gjl8aa/face.tsx";
import Facetxt39mFace from "@/faces/face-txt39m/face.tsx";
import Faceqz9lprFace from "@/faces/face-qz9lpr/face.tsx";
import Faceojv4e4Face from "@/faces/face-ojv4e4/face.tsx";
import Facec8vcnsFace from "@/faces/face-c8vcns/face.tsx";
import Face9d0kbbFace from "@/faces/face-9d0kbb/face.tsx";
import "@/faces/face-6ifrcs/face.css";
import "@/faces/face-rjgam2/face.css";
import "@/faces/face-hodmbt/face.css";
import "@/faces/face-zeoka1/face.css";
import "@/faces/face-cdfv0f/face.css";
import "@/faces/face-2o0r2a/face.css";
import "@/faces/face-o19ezs/face.css";
import "@/faces/face-5f2d3z/face.css";
import "@/faces/face-q1kgxg/face.css";
import "@/faces/face-gjl8aa/face.css";
import "@/faces/face-txt39m/face.css";
import "@/faces/face-qz9lpr/face.css";
import "@/faces/face-ojv4e4/face.css";
import "@/faces/face-c8vcns/face.css";
import "@/faces/face-9d0kbb/face.css";

const visibleFaces = faces.filter((face) => !face.hidden);

export const componentMap = {
  "face-6ifrcs": Face6ifrcsFace,
  "face-rjgam2": Facerjgam2Face,
  "face-hodmbt": FacehodmbtFace,
  "face-zeoka1": Facezeoka1Face,
  "face-cdfv0f": Facecdfv0fFace,
  "face-2o0r2a": Face2o0r2aFace,
  "face-o19ezs": Faceo19ezsFace,
  "face-5f2d3z": Face5f2d3zFace,
  "face-q1kgxg": Faceq1kgxgFace,
  "face-gjl8aa": Facegjl8aaFace,
  "face-txt39m": Facetxt39mFace,
  "face-qz9lpr": Faceqz9lprFace,
  "face-ojv4e4": Faceojv4e4Face,
  "face-c8vcns": Facec8vcnsFace,
  "face-9d0kbb": Face9d0kbbFace,
};

export const projectConfig = {"layout":"STACKED","slidesDisplay":"CARDS","stackedOrientation":"HORIZONTAL","cardsBackgroundColor":"#8e8e86","cardsCorners":"SQUARE","mobileCanvas":"COMPACT","tokens":{"palette":[{"name":"--background","value":"#d7d7d2"},{"name":"--surface","value":"#c9c9c2"},{"name":"--foreground","value":"#1e1f1d"},{"name":"--brand","value":"#f7c600"},{"name":"--accent","value":"#d9531e"},{"name":"--muted","value":"#3a3b38"},{"name":"--paper","value":"#f2f2ee"},{"name":"--line","value":"#b9b9b2"},{"name":"--steel","value":"#8e8e86"},{"name":"--steel-dark","value":"#4d4d47"}],"fonts":[{"name":"--font-display","family":"Oswald"},{"name":"--font-body","family":"Roboto Condensed"}]}};

export default function Page() {
  return (
    <NewSlidesLayout
      faces={visibleFaces}
      componentMap={componentMap}
      layout="STACKED"
      slidesDisplay="CARDS"
      stackedOrientation="HORIZONTAL"
      cardsSlidesPerView={1.25}
      cardsBackgroundColor={"#8e8e86"}
      cardsBackgroundImage={""}
      cardsCorners="SQUARE"
      mobileCanvas="COMPACT"
    />
  );
}