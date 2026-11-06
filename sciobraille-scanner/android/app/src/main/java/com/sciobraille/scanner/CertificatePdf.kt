package com.sciobraille.scanner

import android.graphics.Color
import android.graphics.Paint
import android.graphics.pdf.PdfDocument
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import java.io.OutputStream

/** Unicode-aware certificate export using Android's PDF canvas and text layout. */
object CertificatePdf {
    fun write(text:String, output:OutputStream) {
        require(text.isNotBlank())
        val body=StaticLayout.Builder.obtain(text,0,text.length,TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            color=Color.rgb(23,32,57);textSize=19f
        },499).setAlignment(Layout.Alignment.ALIGN_NORMAL).setLineSpacing(8f,1f).build()
        val document=PdfDocument()
        try {
            var top=0;var number=1
            while(top<body.height) {
                val page=document.startPage(PdfDocument.PageInfo.Builder(595,842,number++).create())
                val canvas=page.canvas
                canvas.drawColor(Color.WHITE)
                canvas.drawText("SCIOBRAILLE",48f,64f,Paint(Paint.ANTI_ALIAS_FLAG).apply { color=Color.rgb(76,59,168);textSize=26f;isFakeBoldText=true })
                canvas.drawText("Certificate of achievement",48f,100f,Paint(Paint.ANTI_ALIAS_FLAG).apply { color=Color.DKGRAY;textSize=18f })
                // Break only between text lines, never across a line of glyphs.
                var end=body.getLineBottom(body.lineCount-1)
                for(line in 0 until body.lineCount) if(body.getLineBottom(line)>top+650) {
                    end=if(line>0) body.getLineBottom(line-1) else body.getLineBottom(line);break
                }
                canvas.save();canvas.clipRect(48f,145f,547f,145f+(end-top));canvas.translate(48f,145f-top);body.draw(canvas);canvas.restore()
                document.finishPage(page);top=end
            }
            document.writeTo(output)
        } finally { document.close() }
    }
}
