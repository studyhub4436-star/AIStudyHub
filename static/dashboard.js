// ===============================
// SHOW SECTIONS
// ===============================
function showSection(sectionId, element) {
  // Hide all sections
  let sections = document.querySelectorAll(".content");
  sections.forEach(function (section) {
    section.classList.remove("active");
  });

  // Show selected section
  document.getElementById(sectionId).classList.add("active");

  // Remove active menu
  let menuItems = document.querySelectorAll(".sidebar ul li");
  menuItems.forEach(function (item) {
    item.classList.remove("active");
  });

  // Active menu
  if (element) {
    element.classList.add("active");
  }

  // Close sidebar on mobile
  if (window.innerWidth <= 768) {
    document.querySelector(".sidebar").classList.remove("active");
  }

  // If search section is opened, run search immediately to show initial list
  if (sectionId === "search") {
    runSearch();
  }
}

// ===============================
// MOBILE SIDEBAR
// ===============================
function toggleSidebar() {
  document.querySelector(".sidebar").classList.toggle("active");
}

// ===============================
// EDIT PROFILE
// ===============================
function editProfile() {
  document.getElementById("editModal").style.display = "flex";

  document.getElementById("editName").value =
    document.getElementById("profileName").innerText;

  document.getElementById("editEmail").value = document
    .getElementById("profileEmail")
    .innerText.replace("📧 ", "")
    .trim();

  document.getElementById("editBranch").value = document
    .getElementById("profileBranch")
    .innerText.replace("🏫 ", "")
    .trim();

  document.getElementById("editYear").value = document
    .getElementById("profileYear")
    .innerText.replace("📚 ", "")
    .trim();
}

// ===============================
// CLOSE MODAL
// ===============================
function closeModal() {
  document.getElementById("editModal").style.display = "none";
}

// ===============================
// SAVE PROFILE
// ===============================
function saveProfile() {
  let name = document.getElementById("editName").value.trim();
  let email = document.getElementById("editEmail").value.trim();
  let branch = document.getElementById("editBranch").value;
  let year = document.getElementById("editYear").value;

  if (name === "" || email === "") {
    alert("❌ Name and Email cannot be empty.");
    return;
  }

  fetch("/api/profile/update", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, email, branch, year }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        alert("✅ Profile Updated Successfully");
        closeModal();
        window.location.reload(); // Reload to reflect changes dynamically
      } else {
        alert("❌ " + data.error);
      }
    })
    .catch((err) => {
      console.error(err);
      alert("❌ Failed to update profile. Please try again.");
    });
}

// ===============================
// LOGOUT
// ===============================
function logout() {
  if (confirm("Are you sure you want to logout?")) {
    window.location.href = "/logout";
  }
}

// ===============================
// SEARCH
// ===============================
function runSearch() {
  let query = document.getElementById("subjectSearch").value.trim();
  let branch = document.getElementById("searchBranch").value;
  let year = document.getElementById("searchYear").value;

  let container = document.getElementById("searchResultsContainer");

  // Construct search API URL
  let url = `/api/search?q=${encodeURIComponent(query)}&branch=${encodeURIComponent(branch)}&year=${encodeURIComponent(year)}`;

  fetch(url)
    .then((res) => res.json())
    .then((docs) => {
      container.innerHTML = "";

      if (docs.length === 0) {
        container.innerHTML = `<p style="color: #cbd5e1; padding: 20px 0;">No matching study materials found.</p>`;
        return;
      }

      docs.forEach((doc) => {
        let similarityLabel = "";
        if (doc.score !== undefined && query !== "") {
          let scorePct = Math.round(doc.score * 100);
          similarityLabel = ` <span style="color: #00ffff; font-size: 13px; margin-left: 10px;">(Match: ${scorePct}%)</span>`;
        }

        let card = document.createElement("div");
        card.className = "result-card";
        card.style.marginBottom = "15px";

        card.innerHTML = `
  <h3>${doc.title}${similarityLabel}</h3>
  <p>${doc.branch} | ${doc.year} | ${doc.subject}</p>
  <p style="color: #94a3b8; font-size: 13px; margin-top: 5px;">Downloads: ${doc.downloads || 0}</p>

  <button onclick="downloadFile('${doc.id || doc._id}')">Download</button>

  <button onclick="previewFile('${doc.id || doc._id}')">Preview</button>
`;
        container.appendChild(card);
      });
    })
    .catch((err) => {
      console.error("Search error:", err);
      container.innerHTML = `<p style="color: #ef4444; padding: 20px 0;">An error occurred while searching.</p>`;
    });
}
// ===============================
// UPLOAD FORM
// ===============================
let uploadForm = document.getElementById("uploadForm");
if (uploadForm) {
  uploadForm.addEventListener("submit", function (e) {
    e.preventDefault();

    let title = document.getElementById("uploadTitle").value.trim();
    let description = document.getElementById("uploadDescription").value.trim();
    let branch = document.getElementById("uploadBranch").value;
    let year = document.getElementById("uploadYear").value;
    let subject = document.getElementById("uploadSubject").value.trim();
    // Subject should not contain numbers
    if (/\d/.test(subject)) {
      alert("❌ Subject name should not contain numbers.");
      return;
    }
    let fileInput = document.getElementById("uploadFile");

    if (fileInput.files.length === 0) {
      alert("❌ Please select a PDF file to upload.");
      return;
    }

    let file = fileInput.files[0];

    let formData = new FormData();
    formData.append("title", title);
    formData.append("description", description);
    formData.append("branch", branch);
    formData.append("year", year);
    formData.append("subject", subject);
    formData.append("file", file);

    let submitBtn = uploadForm.querySelector("button[type='submit']");
    submitBtn.disabled = true;
    submitBtn.innerText = "Uploading PDF...";

    fetch("/api/upload", {
      method: "POST",
      body: formData,
    })
      .then((res) => res.json())
      .then((data) => {
        submitBtn.disabled = false;
        submitBtn.innerText = "Upload PDF";

        if (data.success) {
          alert("✅ " + data.message);
          uploadForm.reset();

          // Update list without page refresh
          runSearch();
        } else {
          alert("❌ " + data.error);
        }
      })
      .catch((err) => {
        submitBtn.disabled = false;
        submitBtn.innerText = "Upload PDF";
        console.error("Upload error:", err);
        alert("❌ Upload failed. Please try again.");
      });
  });
}
window.onclick = function (event) {
  let modal = document.getElementById("editModal");
  if (event.target == modal) {
    closeModal();
  }
};
// ===============================
// CLOSE MODAL ON OUTSIDE CLICK
// ===============================
window.onload = function () {
  let firstMenu = document.querySelector(".sidebar ul li");
  if (firstMenu) {
    firstMenu.classList.add("active");
  }

  setInterval(runSearch, 10000);
};

// ===============================
// DOWNLOAD HELPER
// ===============================
function downloadFile(docId) {
  window.location.href = "/api/download/" + docId;
}

// ===============================
// PDF PREVIEW
// ===============================
// ===============================
// PDF PREVIEW - SEARCH
// ===============================
function previewFile(docId) {
  showSection("search");

  let viewer = document.getElementById("pdfViewer");
  let container = document.getElementById("pdfPreviewContainer");

  viewer.src = "/preview/" + docId;
  viewer.style.display = "block";
  container.style.display = "block";

  container.scrollIntoView({ behavior: "smooth" });
}
// ===============================
// TRENDING PDF PREVIEW
// ===============================
function previewTrending(docId) {
  let viewer = document.getElementById("trendingPdfViewer");
  let container = document.getElementById("trendingPreviewContainer");

  viewer.src = "/preview/" + docId;
  container.style.display = "block";

  container.scrollIntoView({ behavior: "smooth" });
}

// ===============================
// RECOMMENDATION PDF PREVIEW
// ===============================
function previewRecommendation(docId) {
  let viewer = document.getElementById("recommendationPdfViewer");
  let container = document.getElementById("recommendationPreviewContainer");

  viewer.src = "/preview/" + docId;
  container.style.display = "block";

  container.scrollIntoView({ behavior: "smooth" });
}