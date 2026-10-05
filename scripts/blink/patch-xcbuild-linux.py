#!/usr/bin/env python3
"""Patch legacy xcbuild for Linux and add the missing iOS product specifications."""

from __future__ import annotations

import sys
from pathlib import Path


def patch_dependency_resolver(xcbuild_root: Path) -> None:
    source = (
        xcbuild_root
        / "Libraries"
        / "pbxbuild"
        / "Sources"
        / "Build"
        / "DependencyResolver.cpp"
    )
    contents = source.read_text(encoding="utf-8")
    original = (
        "        for (pbxproj::PBX::BuildFile::shared_ptr const &file : buildPhase->files()) {\n"
        "            switch (file->fileRef()->type()) {"
    )
    patched = (
        "        for (pbxproj::PBX::BuildFile::shared_ptr const &file : buildPhase->files()) {\n"
        "            if (file == nullptr || file->fileRef() == nullptr) {\n"
        "                continue;\n"
        "            }\n"
        "            switch (file->fileRef()->type()) {"
    )

    if patched in contents:
        return
    if contents.count(original) != 1:
        raise SystemExit(f"expected one DependencyResolver patch anchor in {source}")
    source.write_text(contents.replace(original, patched, 1), encoding="utf-8", newline="\n")


def patch_symlink_resolver(xcbuild_root: Path) -> None:
    source = xcbuild_root / "Libraries/pbxbuild/Sources/Tool/SymlinkResolver.cpp"
    contents = source.read_text(encoding="utf-8")
    original = 'invocation.arguments() = { "-sfh", targetPath, symlinkPath };'
    patched = 'invocation.arguments() = { "-sfn", targetPath, symlinkPath };'

    if patched in contents:
        return
    if contents.count(original) != 1:
        raise SystemExit(f"expected one SymlinkResolver patch anchor in {source}")
    source.write_text(contents.replace(original, patched, 1), encoding="utf-8", newline="\n")


def patch_ios_framework_layout(xcbuild_root: Path) -> None:
    source = xcbuild_root / "Libraries/pbxbuild/Sources/Phase/ProductTypeResolver.cpp"
    contents = source.read_text(encoding="utf-8")
    original = (
        "    if (Tool::SymlinkResolver const *symlinkResolver = phaseContext->symlinkResolver(phaseEnvironment)) {\n"
        '        std::string versions = environment.resolve("VERSIONS_FOLDER_PATH");'
    )
    patched = (
        '    std::string platformName = environment.resolve("PLATFORM_NAME");\n'
        '    if (platformName == "iphoneos" || platformName == "iphonesimulator") {\n'
        "        return true;\n"
        "    }\n\n"
        + original
    )

    if patched in contents:
        return
    if contents.count(original) != 1:
        raise SystemExit(f"expected one framework-layout patch anchor in {source}")
    source.write_text(contents.replace(original, patched, 1), encoding="utf-8", newline="\n")


def patch_build_rule_type_matching(xcbuild_root: Path) -> None:
    source = xcbuild_root / "Libraries/pbxbuild/Sources/Target/BuildRules.cpp"
    contents = source.read_text(encoding="utf-8")
    original = (
        "                if (std::find(fileTypes.begin(), fileTypes.end(), FT) != fileTypes.end()) {\n"
        "                    return buildRule;\n"
        "                }"
    )
    patched = (
        "                for (pbxspec::PBX::FileType::shared_ptr const &ruleFileType : fileTypes) {\n"
        "                    if (ruleFileType->identifier() == FT->identifier()) {\n"
        "                        return buildRule;\n"
        "                    }\n"
        "                }"
    )

    if patched in contents:
        return
    if contents.count(original) != 1:
        raise SystemExit(f"expected one BuildRules file-type patch anchor in {source}")
    source.write_text(contents.replace(original, patched, 1), encoding="utf-8", newline="\n")


def patch_clang_synthesized_build_rule(xcbuild_root: Path) -> None:
    source = xcbuild_root / "Specifications/Compiler/com.apple.compilers.llvm.clang.1_0.xcspec"
    contents = source.read_text(encoding="utf-8")
    anchor = '    Identifier = com.apple.compilers.llvm.clang.1_0;\n'
    patched = anchor + "    SynthesizeBuildRule = YES;\n"

    if "    SynthesizeBuildRule = YES;" in contents:
        return
    if contents.count(anchor) != 1:
        raise SystemExit(f"expected one Clang specification anchor in {source}")
    source.write_text(contents.replace(anchor, patched, 1), encoding="utf-8", newline="\n")


def patch_clang_tool_dispatch(xcbuild_root: Path) -> None:
    source = xcbuild_root / "Libraries/pbxbuild/Sources/Phase/Context.cpp"
    contents = source.read_text(encoding="utf-8")
    original = "} else if (toolIdentifier == Tool::ClangResolver::ToolIdentifier()) {"
    patched = (
        "} else if (toolIdentifier == Tool::ClangResolver::ToolIdentifier() || "
        'toolIdentifier == "com.apple.compilers.llvm.clang.1_0") {'
    )

    if patched in contents:
        return
    if contents.count(original) != 1:
        raise SystemExit(f"expected one Clang tool-dispatch anchor in {source}")
    source.write_text(contents.replace(original, patched, 1), encoding="utf-8", newline="\n")


def stage_ios_product_types(xcbuild_root: Path) -> None:
    source = Path(__file__).with_name("linux-ios-product-types.xcspec")
    destination = xcbuild_root / "Specifications" / "HermesLink-iOS-ProductTypes.xcspec"
    destination.parent.mkdir(parents=True, exist_ok=True)
    contents = source.read_text(encoding="utf-8")
    if not destination.exists() or destination.read_text(encoding="utf-8") != contents:
        destination.write_text(contents, encoding="utf-8", newline="\n")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} XCBUILD_SOURCE_ROOT")
    xcbuild_root = Path(sys.argv[1])
    patch_dependency_resolver(xcbuild_root)
    patch_symlink_resolver(xcbuild_root)
    patch_ios_framework_layout(xcbuild_root)
    patch_build_rule_type_matching(xcbuild_root)
    patch_clang_synthesized_build_rule(xcbuild_root)
    patch_clang_tool_dispatch(xcbuild_root)
    stage_ios_product_types(xcbuild_root)


if __name__ == "__main__":
    main()
