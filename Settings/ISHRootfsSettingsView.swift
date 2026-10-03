import SwiftUI
import UniformTypeIdentifiers

struct ISHRootfsSettingsView: View {
  @State private var profiles: [String] = []
  @State private var activeProfile = ""
  @State private var newName = ""
  @State private var editingProfile: String?
  @State private var profilePendingDeletion: String?
  @State private var showingNameSheet = false
  @State private var showingDeleteConfirmation = false
  @State private var showingImporter = false
  @State private var showingError = false
  @State private var errorMessage = ""
  @State private var restartRequired = false
  @State private var documentsAutoMount = false
  @State private var documentsMountPath = "/mnt/documents"
  @State private var documentsMask = "0022"
  @State private var isBusy = false

  var body: some View {
    List {
      Section {
        ForEach(profiles, id: \.self) { profile in
          HStack {
            Button {
              select(profile)
            } label: {
              HStack {
                Text(profile)
                Spacer()
                if !ISHRootfsProfileIsValid(profile) {
                  Text("Not installed")
                    .foregroundColor(.secondary)
                    .font(.footnote)
                } else if profile == activeProfile {
                  Image(systemName: "checkmark")
                    .foregroundColor(.accentColor)
                }
              }
              .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            Menu {
              Button("Use Profile") { select(profile) }
              Button("Rename") {
                editingProfile = profile
                newName = profile
                showingNameSheet = true
              }
              Button("Delete", role: .destructive) {
                profilePendingDeletion = profile
                showingDeleteConfirmation = true
              }
            } label: {
              Image(systemName: "ellipsis.circle")
                .foregroundColor(.secondary)
            }
          }
        }
      } header: {
        Text("Rootfs profiles")
      } footer: {
        Text("Each rootfs profile is stored in its own folder under Documents/iSH; this location is visible in Files.")
      }

      Section {
        Button {
          editingProfile = nil
          newName = ""
          showingNameSheet = true
        } label: {
          Label("Create a copy of the active rootfs", systemImage: "plus")
        }
        Button {
          showingImporter = true
        } label: {
          Label("Import rootfs folder or .tar.gz", systemImage: "square.and.arrow.down")
        }
      }

      Section {
        Toggle("Automatically mount Documents", isOn: $documentsAutoMount)
        TextField("Guest mount path", text: $documentsMountPath)
          .textInputAutocapitalization(.never)
          .autocorrectionDisabled()
        TextField("Permission mask (octal)", text: $documentsMask)
          .textInputAutocapitalization(.never)
          .autocorrectionDisabled()
        Button("Save Documents mount settings", action: saveDocumentsMount)
      } header: {
        Text("Documents mount")
      } footer: {
        Text("Mounts Files-visible Documents directly without fakefs metadata. Unix permissions and symlinks are not supported. The mask controls guest-visible modes; mount changes apply after restarting iSH.")
      }

      if restartRequired {
        Section {
          Label("Force-quit and reopen Blink for the saved iSH settings to take effect.", systemImage: "arrow.clockwise")
            .font(.footnote)
            .foregroundColor(.secondary)
        }
      }
    }
    .navigationTitle("iSH")
    .toolbar {
      ToolbarItem(placement: .navigationBarTrailing) {
        Menu {
          Button("Create a copy") {
            editingProfile = nil
            newName = ""
            showingNameSheet = true
          }
          Button("Import rootfs…") { showingImporter = true }
        } label: {
          Image(systemName: "plus")
        }
        .disabled(isBusy)
      }
    }
    .disabled(isBusy)
    .overlay {
      if isBusy {
        ProgressView()
          .padding()
          .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
      }
    }
    .onAppear {
      reload()
      documentsAutoMount = ISHDocumentsAutoMountEnabled()
      documentsMountPath = ISHDocumentsGuestMountPath()
      let mask = String(ISHDocumentsMountMask(), radix: 8)
      documentsMask = String(repeating: "0", count: max(0, 4 - mask.count)) + mask
      restartRequired = !documentsConfigurationIsCurrent()
    }
    .sheet(isPresented: $showingNameSheet) {
      NavigationView {
        Form {
          TextField("Profile name", text: $newName)
            .autocapitalization(.none)
            .disableAutocorrection(true)
        }
        .navigationTitle(editingProfile == nil ? "New iSH Profile" : "Rename iSH Profile")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
          ToolbarItem(placement: .cancellationAction) {
            Button("Cancel") { showingNameSheet = false }
          }
          ToolbarItem(placement: .confirmationAction) {
            Button(editingProfile == nil ? "Create" : "Save", action: saveName)
              .disabled(newName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isBusy)
          }
        }
      }
      .presentationDetents([.medium])
    }
    .fileImporter(
      isPresented: $showingImporter,
      allowedContentTypes: [.folder, .archive, .gzip]
    ) { result in
      switch result {
      case .success(let url):
        importProfile(from: url)
      case .failure(let error):
        showError(error.localizedDescription)
      }
    }
    .confirmationDialog(
      "Delete the rootfs profile?",
      isPresented: $showingDeleteConfirmation,
      titleVisibility: .visible
    ) {
      Button("Delete", role: .destructive) {
        guard let profile = profilePendingDeletion else { return }
        perform {
          var error: NSError?
          return ISHRootfsDeleteProfile(profile, &error) ? nil : error
        }
      }
    } message: {
      Text("This permanently removes all files in the selected profile.")
    }
    .alert("iSH", isPresented: $showingError) {
      Button("OK", role: .cancel) {}
    } message: {
      Text(errorMessage)
    }
  }

  private func reload() {
    var error: NSError?
    guard ISHRootfsProfilesPrepare(&error),
          let names = ISHRootfsProfileNames(&error),
          let active = ISHRootfsActiveProfileName(&error) else {
      showError(error?.localizedDescription ?? "Could not load rootfs profiles.")
      return
    }
    profiles = names
    activeProfile = active
  }

  private func saveDocumentsMount() {
    guard let mask = UInt(documentsMask, radix: 8), mask <= 0o777 else {
      showError("The permission mask must be octal and between 0000 and 0777.")
      return
    }
    var error: NSError?
    guard ISHDocumentsMountConfigure(documentsAutoMount, documentsMountPath,
                                     mask, &error) else {
      showError(error?.localizedDescription ?? "Could not save Documents mount settings.")
      return
    }
    restartRequired = !documentsConfigurationIsCurrent()
  }

  private func documentsConfigurationIsCurrent() -> Bool {
    let hostPath = documentsAutoMount ? ISHDocumentsHostPath() : ""
    guard let hostPathCString = hostPath.cString(using: .utf8),
          let mountPathCString = documentsMountPath.cString(using: .utf8),
          let mask = UInt(documentsMask, radix: 8) else {
      return false
    }
    return hostPathCString.withUnsafeBufferPointer { hostPathBuffer in
      mountPathCString.withUnsafeBufferPointer { mountPathBuffer in
        ish_documents_configuration_is_current(
          hostPathBuffer.baseAddress, mountPathBuffer.baseAddress, UInt32(mask)) != 0
      }
    }
  }

  private func select(_ profile: String) {
    let selectedDifferentProfile = profile != activeProfile
    perform({
      var error: NSError?
      return ISHRootfsSelectProfile(profile, &error) ? nil : error
    }, onSuccess: {
      restartRequired = selectedDifferentProfile || restartRequired
    })
  }

  private func saveName() {
    let name = newName.trimmingCharacters(in: .whitespacesAndNewlines)
    let oldName = editingProfile
    showingNameSheet = false
    perform {
      var error: NSError?
      if let oldName {
        return ISHRootfsRenameProfile(oldName, name, &error) ? nil : error
      }
      return ISHRootfsCreateProfile(name, &error) ? nil : error
    }
  }

  private func importProfile(from url: URL) {
    var name = url.lastPathComponent
    if name.lowercased().hasSuffix(".tar.gz") {
      name = String(name.dropLast(7))
    } else if name.lowercased().hasSuffix(".tgz") {
      name = String(name.dropLast(4))
    }
    let profileName = name
    perform {
      let hasAccess = url.startAccessingSecurityScopedResource()
      defer {
        if hasAccess {
          url.stopAccessingSecurityScopedResource()
        }
      }
      var coordinationError: NSError?
      var importError: NSError?
      let coordinator = NSFileCoordinator()
      coordinator.coordinate(readingItemAt: url, options: .withoutChanges, error: &coordinationError) { coordinatedURL in
        if !ISHRootfsImportProfile(profileName, coordinatedURL, &importError) {
          return
        }
      }
      return importError ?? coordinationError
    }
  }

  private func perform(_ operation: @escaping () -> NSError?, onSuccess: (() -> Void)? = nil) {
    isBusy = true
    DispatchQueue.global(qos: .userInitiated).async {
      let error = operation()
      DispatchQueue.main.async {
        isBusy = false
        if let error {
          showError(error.localizedDescription)
        } else {
          onSuccess?()
          reload()
        }
      }
    }
  }

  private func showError(_ message: String) {
    errorMessage = message
    showingError = true
  }
}
