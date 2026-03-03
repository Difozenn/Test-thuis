using System;
using System.IO;
using System.Windows.Forms;

class Program
{
    [STAThread]
    static void Main()
    {
        Application.EnableVisualStyles();

        Form form = new Form();
        form.Text = "Joblist Tool";
        form.Width = 290;
        form.Height = 120;
        form.FormBorderStyle = FormBorderStyle.FixedSingle;
        form.MaximizeBox = false;
        form.StartPosition = FormStartPosition.CenterScreen;

        Button btn = new Button();
        btn.Text = "Joblist Leegmaken";
        btn.Width = 200;
        btn.Height = 40;
        btn.Left = 35;
        btn.Top = 20;

        btn.Click += delegate
        {
            if (MessageBox.Show("Workcenter afsluiten voor leegmaken",
                "Bevestiging", MessageBoxButtons.OKCancel,
                MessageBoxIcon.Warning) == DialogResult.OK)
            {
                string path = @"C:\joblist\joblist.ini";
                try
                {
                    File.WriteAllText(path, string.Empty);
                    MessageBox.Show("Joblist is leeggemaakt.",
                        "Gereed", MessageBoxButtons.OK,
                        MessageBoxIcon.Information);
                }
                catch
                {
                    MessageBox.Show("Kan bestand niet openen:\n" + path,
                        "Fout", MessageBoxButtons.OK,
                        MessageBoxIcon.Error);
                }
            }
        };

        form.Controls.Add(btn);
        Application.Run(form);
    }
}
