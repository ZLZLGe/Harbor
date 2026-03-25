ThisBuild / scalaVersion := "2.13.12"

lazy val root = project
  .in(file("."))
  .settings(
    name := "scala-feature-flags",
    libraryDependencies += "org.scalatest" %% "scalatest" % "3.2.19" % Test
  )
