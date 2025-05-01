from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton, QScrollArea
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt
import subprocess
import webbrowser

from .. import config
from ..i18n import _, get_translator

# Initialize the translator
translator = get_translator()

class AboutPage(QWidget):
    """Widget for displaying the About page content."""
    def __init__(self, parent=None):
        super().__init__(parent)
        # Create a scroll area for About content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        # Main layout for this widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll, 1)
        # Layout for content inside scroll area
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header: Logo and Title
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)

        # App logo
        logo_label = QLabel()
        logo_label.setObjectName("about_logo")
        logo_size = 96
        if config.WINDOW_ICON:
            pix = QPixmap(config.WINDOW_ICON).scaled(
                logo_size, logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_label.setPixmap(pix)
        else:
            pix = QPixmap(logo_size, logo_size)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor("#1a73e8"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(8, 8, logo_size-16, logo_size-16, 12, 12)
            painter.setPen(QColor("white"))
            font = QFont()
            font.setPointSize(40)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "A")
            painter.end()
            logo_label.setPixmap(pix)
        header_layout.addWidget(logo_label)

        # Title and version
        title_layout = QVBoxLayout()
        title_label = QLabel(f"<h1>{config.APP_NAME}</h1>")
        title_label.setObjectName("about_title")
        version_parts = config.APP_VERSION.split('.')
        if len(version_parts) >= 3:
            major, minor, patch = version_parts[0], version_parts[1], version_parts[2]
            build = ""
            if '-' in patch:
                patch, suffix = patch.split('-', 1)
                build = '-' + suffix
            version_text = f"<h3>v{major}.{minor}.{patch}<span style='font-size:80%;'>{build}</span></h3>"
        else:
            version_text = f"<h3>v{config.APP_VERSION}</h3>"
        version_label = QLabel(version_text)
        version_label.setObjectName("about_version")
        title_layout.addWidget(title_label)
        title_layout.addWidget(version_label)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header_layout.addLayout(title_layout, 1)
        layout.addWidget(header_widget)

        # Description
        desc_label = QLabel(_("about_description"))
        desc_label.setObjectName("about_description")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignJustify)
        layout.addWidget(desc_label)
        # Keep reference for retranslation
        self.desc_label = desc_label

        # Features list
        features_group = QGroupBox(_("about_features"))
        features_group.setObjectName("about_features_group")
        # Keep reference for retranslation
        self.features_group = features_group
        self.feature_labels = []
        features_layout = QVBoxLayout(features_group)
        # Improve spacing and margins to avoid overlapping text
        features_layout.setSpacing(12)
        features_layout.setContentsMargins(15, 15, 15, 15)
        features = [
            _("about_feature_extract"),
            _("about_feature_desktop"),
            _("about_feature_icon"),
            _("about_feature_manage"),
            _("about_feature_launch"),
        ]
        for i, feat in enumerate(features):
            lbl = QLabel(feat)
            lbl.setWordWrap(True)
            # Add bottom margin for each label
            lbl.setContentsMargins(0, 0, 0, 8)
            lbl.setObjectName(f"about_feature_{i}")
            # Keep reference for retranslation
            self.feature_labels.append(lbl)
            features_layout.addWidget(lbl)
        layout.addWidget(features_group)

        # Developer information
        dev_group = QGroupBox(_("about_developer_info"))
        dev_group.setObjectName("about_developer_group")
        # Keep reference for developer info labels
        self.dev_group = dev_group
        self.dev_labels = []
        dev_layout = QVBoxLayout(dev_group)
        dev_infos = [
            f"<b>{_('about_developer_name')}:</b> Tuncay Eşsiz",
            f"<b>{_('about_github_profile')}:</b> <a href='https://github.com/tunjayoff'>github.com/tunjayoff</a>",
            f"<b>{_('about_github_project')}:</b> <a href='https://github.com/tunjayoff/appimagemanager'>github.com/tunjayoff/appimagemanager</a>",
            f"<b>{_('about_license')}:</b> MIT",
        ]
        for i, txt in enumerate(dev_infos):
            lbl = QLabel(txt)
            lbl.setObjectName(f"about_dev_info_{i}")
            lbl.setOpenExternalLinks(True)
            # Keep reference for retranslation
            self.dev_labels.append(lbl)
            dev_layout.addWidget(lbl)
        layout.addWidget(dev_group)

        # System information
        sys_group = QGroupBox(_("about_system_info"))
        sys_group.setObjectName("about_system_group")
        # Keep reference for system info labels and values
        self.sys_group = sys_group
        try:
            distro = subprocess.check_output(["lsb_release", "-ds"]).decode().strip().strip('"')
        except:
            distro = "Unknown"
        py_ver = subprocess.check_output(["python3", "--version"]).decode().split()[1]
        qt_ver = QApplication.instance().applicationVersion()
        # Store values for retranslation
        self.sys_values = [distro, f"Python {py_ver}", f"Qt {qt_ver}"]
        self.sys_labels = []
        sys_layout = QVBoxLayout(sys_group)
        sys_infos = [
            f"<b>{_('about_os')}:</b> {distro}",
            f"<b>{_('about_python')}:</b> Python {py_ver}",
            f"<b>{_('about_qt')}:</b> Qt {qt_ver}",
        ]
        for i, txt in enumerate(sys_infos):
            lbl = QLabel(txt)
            lbl.setObjectName(f"about_sys_info_{i}")
            # Keep reference for retranslation
            self.sys_labels.append(lbl)
            sys_layout.addWidget(lbl)
        layout.addWidget(sys_group)

        # Buttons
        btn_layout = QHBoxLayout()
        website_btn = QPushButton(_("about_website"))
        website_btn.setObjectName("about_website_btn")
        website_btn.clicked.connect(lambda: webbrowser.open("https://github.com/tunjayoff/appimagemanager"))
        # Keep reference for retranslation
        self.website_btn = website_btn
        report_btn = QPushButton(_("about_report_issue"))
        report_btn.setObjectName("about_report_btn")
        report_btn.clicked.connect(lambda: webbrowser.open("https://github.com/tunjayoff/appimagemanager/issues"))
        # Keep reference for retranslation
        self.report_btn = report_btn
        btn_layout.addWidget(website_btn)
        btn_layout.addWidget(report_btn)
        layout.addLayout(btn_layout)

        # Spacer to push content up
        layout.addStretch(1)

    def retranslateUi(self):
        """Update all UI texts when language changes."""
        translator = get_translator()
        # Description
        self.desc_label.setText(translator.get_text("about_description"))
        # Features
        self.features_group.setTitle(translator.get_text("about_features"))
        keys = [
            "about_feature_extract", "about_feature_desktop",
            "about_feature_icon", "about_feature_manage",
            "about_feature_launch"
        ]
        for lbl, key in zip(self.feature_labels, keys):
            lbl.setText(translator.get_text(key))
        # Developer group title
        self.dev_group.setTitle(translator.get_text("about_developer_info"))
        # System group title
        self.sys_group.setTitle(translator.get_text("about_system_info"))
        # Buttons
        self.website_btn.setText(translator.get_text("about_website"))
        self.report_btn.setText(translator.get_text("about_report_issue"))
        # Update developer info labels
        dev_keys = [
            "about_developer_name", "about_github_profile",
            "about_github_project", "about_license"
        ]
        for i, lbl in enumerate(self.dev_labels):
            key = dev_keys[i]
            if key == "about_developer_name":
                lbl.setText(f"<b>{translator.get_text(key)}:</b> Tuncay Eşsiz")
            elif key == "about_github_profile":
                lbl.setText(f"<b>{translator.get_text(key)}:</b> <a href='https://github.com/tunjayoff'>github.com/tunjayoff</a>")
            elif key == "about_github_project":
                lbl.setText(f"<b>{translator.get_text(key)}:</b> <a href='https://github.com/tunjayoff/appimagemanager'>github.com/tunjayoff/appimagemanager</a>")
            elif key == "about_license":
                lbl.setText(f"<b>{translator.get_text(key)}:</b> MIT")

        # Update system information labels
        sys_keys = ["python_version", "qt_version", "os_version", "desktop_environment"]
        for i, lbl in enumerate(self.sys_labels):
            key = sys_keys[i]
            lbl.setText(f"<b>{translator.get_text(key)}:</b> {self.sys_values[i]}")

    def open_link(self, url):
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Error: Failed to open link {url}: {e}") # Simple print fallback 