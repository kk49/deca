// gcc -fPIC -shared -O3 process_image.c -o process_image.so

#ifdef __cplusplus
extern "C" {
#endif

#ifdef _WINDLL
#define DLLEXPORT   __declspec( dllexport )
#else
#define DLLEXPORT
#endif

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;

DLLEXPORT
int process_image(
    u8 * dst_image_buf,
    u32 dst_image_sz,
    u8 const * src_buffer_buf,
    u32 src_buffer_sz,
    u32 nx,
    u32 ny,
    u32 pixel_format
    )
{
    switch(pixel_format)
    {

        case 10:
            {
                u8 * optr = (u8 *)dst_image_buf;
                u16 const * iptr = (u16 const*)src_buffer_buf;
                //TODO check lengths for buffer overruns
                for(u32 yi = 0; yi < ny; ++yi)
                {
                    for(u32 xi = 0; xi < nx; ++xi)
                    {
                        *optr = *iptr >> 8; optr += 1; iptr += 1;
                        *optr = *iptr >> 8; optr += 1; iptr += 1;
                        *optr = *iptr >> 8; optr += 1; iptr += 1;
                        *optr = *iptr >> 8; optr += 1; iptr += 1;
                    }
                }
                return 0;
            }
            break;
        case 26:
            {
                u8 * optr = (u8 *)dst_image_buf;
                u32 const * iptr = (u32 const*)src_buffer_buf;
                //TODO check lengths for buffer overruns
                for(u32 yi = 0; yi < ny; ++yi)
                {
                    for(u32 xi = 0; xi < nx; ++xi)
                    {
                        optr[0] = ((*iptr >> 21) & 0x07ff) >> 3;
                        optr[1] = ((*iptr >> 10) & 0x07ff) >> 3;
                        optr[2] = ((*iptr >> 0) & 0x03ff) >> 2;
                        optr[3] = 0xFF;
                        optr += 4;
                        iptr += 1;
                    }
                }
                return 0;
            }
            break;
        case 28:
            {
                u8 * optr = dst_image_buf;
                u8 const * iptr = src_buffer_buf;
                //TODO check lengths for buffer overruns
                for(u32 yi = 0; yi < ny; ++yi)
                {
                    for(u32 xi = 0; xi < nx; ++xi)
                    {
                        optr[0] = iptr[0];
                        optr[1] = iptr[1];
                        optr[2] = iptr[2];
                        optr[3] = iptr[3];
                        optr += 4;
                        iptr += 4;
                    }
                }
                return 0;
            }
            break;
        case 87:
            {
                u8 * optr = dst_image_buf;
                u8 const * iptr = src_buffer_buf;
                //TODO check lengths for buffer overruns
                for(u32 yi = 0; yi < ny; ++yi)
                {
                    for(u32 xi = 0; xi < nx; ++xi)
                    {
                        optr[0] = iptr[2];
                        optr[1] = iptr[1];
                        optr[2] = iptr[0];
                        optr[3] = iptr[3];
                        optr += 4;
                        iptr += 4;
                    }
                }
                return 0;
            }
            break;
        case 71:
            {
                if(nx < 4) nx = 4;
                if(ny < 4) ny = 4;
                u32 bnx = nx >> 2;
                u32 bny = ny >> 2;
                u8 const * iptr = src_buffer_buf;
                for(u32 yo = 0; yo < bny; ++yo)
                {
                    for(u32 xo = 0;  xo < bnx; ++xo)
                    {
                        u16 color0 = *((u16 const*)(iptr + 0));
                        u16 color1 = *((u16 const*)(iptr + 2));
                        u32 cidx = *((u32 const*)(iptr + 4));
                        iptr += 8;

                        u8 colors8[16];
                        u32 const* colors = (u32 const*)colors8;

                        colors8[0*4 + 0] = ((color0 >> 11) & 0x1F) << 3;
                        colors8[0*4 + 1] = ((color0 >>  5) & 0x3F) << 2;
                        colors8[0*4 + 2] = ((color0 >>  0) & 0x1F) << 3;
                        colors8[0*4 + 3] = 0xFF;
                        colors8[1*4 + 0] = ((color1 >> 11) & 0x1F) << 3;
                        colors8[1*4 + 1] = ((color1 >>  5) & 0x3F) << 2;
                        colors8[1*4 + 2] = ((color1 >>  0) & 0x1F) << 3;
                        colors8[1*4 + 3] = 0xFF;

                        if(color0 > color1)
                        {
                            for(u32 i = 0; i < 3; ++i)
                            {
                                colors8[2*4 + i] = (2 * (u16)colors8[0*4 + i] + (u16)colors8[1*4 + i]) / 3;
                                colors8[3*4 + i] = ((u16)colors8[0*4 + i] + 2 * (u16)colors8[1*4 + i]) / 3;
                            }
                            colors8[2*4 + 3] = 0xFF;
                            colors8[3*4 + 3] = 0xFF;
                        }
                        else
                        {
                            for(u32 i = 0; i < 3; ++i)
                            {
                                colors8[2*4 + i] = (colors8[0*4 + i] + colors8[1*4 + i]) >> 1;
                            }
                            colors8[2*4 + 3] = 0xFF;

                            colors8[3*4 + 0] = 0;
                            colors8[3*4 + 1] = 0;
                            colors8[3*4 + 2] = 0;
                            colors8[3*4 + 3] = 0;
                        }

                        for(u32 yi = 0; yi < 4; ++yi)
                        {
                            u8 * optr = dst_image_buf;
                            optr += xo * 4 * 4;  // block offset in X
                            optr += yo * 4 * 4 * nx; // block offset in Y
                            optr += yi * 4 * nx; // pixel offset in Y
                            for(u32 xi = 0; xi < 4; ++xi)
                            {
                                *((u32*)optr) = colors[cidx & 0x3];
                                cidx = cidx >> 2;
                                optr += 4;
                            }
                        }
                    }
                }
                return 0;
            }
            break;
        case 74:
            {
                if(nx < 4) nx = 4;
                if(ny < 4) ny = 4;
                u32 bnx = nx >> 2;
                u32 bny = ny >> 2;
                u8 const * iptr = src_buffer_buf;
                for(u32 yo = 0; yo < bny; ++yo)
                {
                    for(u32 xo = 0;  xo < bnx; ++xo)
                    {
                        u64 alpha = *((u64 const*)(iptr + 0));
                        iptr += 8;

                        u16 color0 = *((u16 const*)(iptr + 0));
                        u16 color1 = *((u16 const*)(iptr + 2));
                        u32 cidx = *((u32 const*)(iptr + 4));
                        iptr += 8;

                        u8 colors8[16];
                        u32 const* colors = (u32 const*)colors8;

                        colors8[0*4 + 0] = ((color0 >> 11) & 0x1F) << 3;
                        colors8[0*4 + 1] = ((color0 >>  5) & 0x3F) << 2;
                        colors8[0*4 + 2] = ((color0 >>  0) & 0x1F) << 3;
                        colors8[0*4 + 3] = 0xFF;
                        colors8[1*4 + 0] = ((color1 >> 11) & 0x1F) << 3;
                        colors8[1*4 + 1] = ((color1 >>  5) & 0x3F) << 2;
                        colors8[1*4 + 2] = ((color1 >>  0) & 0x1F) << 3;
                        colors8[1*4 + 3] = 0xFF;

                        if(color0 > color1)
                        {
                            for(u32 i = 0; i < 3; ++i)
                            {
                                colors8[2*4 + i] = (2 * (u16)colors8[0*4 + i] + (u16)colors8[1*4 + i]) / 3;
                                colors8[3*4 + i] = ((u16)colors8[0*4 + i] + 2 * (u16)colors8[1*4 + i]) / 3;
                            }
                            colors8[2*4 + 3] = 0xFF;
                            colors8[3*4 + 3] = 0xFF;
                        }
                        else
                        {
                            for(u32 i = 0; i < 3; ++i)
                            {
                                colors8[2*4 + i] = (colors8[0*4 + i] + colors8[1*4 + i]) >> 1;
                            }
                            colors8[2*4 + 3] = 0xFF;

                            colors8[3*4 + 0] = 0;
                            colors8[3*4 + 1] = 0;
                            colors8[3*4 + 2] = 0;
                            colors8[3*4 + 3] = 0;
                        }

                        for(u32 yi = 0; yi < 4; ++yi)
                        {
                            u8 * optr = dst_image_buf;
                            optr += xo * 4 * 4;  // block offset in X
                            optr += yo * 4 * 4 * nx; // block offset in Y
                            optr += yi * 4 * nx; // pixel offset in Y
                            for(u32 xi = 0; xi < 4; ++xi)
                            {
                                *((u32*)optr) = colors[cidx & 0x3];
                                cidx = cidx >> 2;

                                *(optr + 3) = (alpha & 0x0f) << 4;
                                alpha = alpha >> 4;

                                optr += 4;
                            }
                        }
                    }
                }
                return 0;
            }
            break;
        case 77:
            {
                if(nx < 4) nx = 4;
                if(ny < 4) ny = 4;
                u32 bnx = nx >> 2;
                u32 bny = ny >> 2;
                u8 const * iptr = src_buffer_buf;
                for(u32 yo = 0; yo < bny; ++yo)
                {
                    for(u32 xo = 0;  xo < bnx; ++xo)
                    {
                        u8 const alpha_0 = *((u8 const*)(iptr + 0));
                        u8 const alpha_1 = *((u8 const*)(iptr + 1));
                        u64 const a0 = *((u16 const*)(iptr + 2));
                        u64 const a1 = *((u16 const*)(iptr + 4));
                        u64 const a2 = *((u16 const*)(iptr + 6));
                        u64 aidx = a2 << 32 | a1 << 16 | a0;
                        iptr += 8;

                        u8 alpha[8];

                        alpha[0] = alpha_0;
                        alpha[1] = alpha_1;
                        if(alpha_0 > alpha_1)
                        {
                            // 6 interpolated alpha values.
                            alpha[2] = (6 * (u16)alpha_0 + 1 * (u16)alpha_1) / 7;  // bit code 010
                            alpha[3] = (5 * (u16)alpha_0 + 2 * (u16)alpha_1) / 7;  // bit code 011
                            alpha[4] = (4 * (u16)alpha_0 + 3 * (u16)alpha_1) / 7;  // bit code 100
                            alpha[5] = (3 * (u16)alpha_0 + 4 * (u16)alpha_1) / 7;  // bit code 101
                            alpha[6] = (2 * (u16)alpha_0 + 5 * (u16)alpha_1) / 7;  // bit code 110
                            alpha[7] = (1 * (u16)alpha_0 + 6 * (u16)alpha_1) / 7;  // bit code 111
                        }
                        else
                        {
                            // 4 interpolated alpha values.
                            alpha[2] = (4 * (u16)alpha_0 + 1 * (u16)alpha_1) / 5;  // bit code 010
                            alpha[3] = (3 * (u16)alpha_0 + 2 * (u16)alpha_1) / 5;  // bit code 011
                            alpha[4] = (2 * (u16)alpha_0 + 3 * (u16)alpha_1) / 5;  // bit code 100
                            alpha[5] = (1 * (u16)alpha_0 + 4 * (u16)alpha_1) / 5;  // bit code 101
                            alpha[6] = 0;  // bit code 110
                            alpha[7] = 255;  // bit code 111
                        }

                        u16 color0 = *((u16 const*)(iptr + 0));
                        u16 color1 = *((u16 const*)(iptr + 2));
                        u32 cidx = *((u32 const*)(iptr + 4));
                        iptr += 8;

                        u8 colors8[16];
                        u32 const* colors = (u32 const*)colors8;

                        colors8[0*4 + 0] = ((color0 >> 11) & 0x1F) << 3;
                        colors8[0*4 + 1] = ((color0 >>  5) & 0x3F) << 2;
                        colors8[0*4 + 2] = ((color0 >>  0) & 0x1F) << 3;
                        colors8[0*4 + 3] = 0xFF;
                        colors8[1*4 + 0] = ((color1 >> 11) & 0x1F) << 3;
                        colors8[1*4 + 1] = ((color1 >>  5) & 0x3F) << 2;
                        colors8[1*4 + 2] = ((color1 >>  0) & 0x1F) << 3;
                        colors8[1*4 + 3] = 0xFF;

                        if(color0 > color1)
                        {
                            for(u32 i = 0; i < 3; ++i)
                            {
                                colors8[2*4 + i] = (2 * (u16)colors8[0*4 + i] + (u16)colors8[1*4 + i]) / 3;
                                colors8[3*4 + i] = ((u16)colors8[0*4 + i] + 2 * (u16)colors8[1*4 + i]) / 3;
                            }
                            colors8[2*4 + 3] = 0xFF;
                            colors8[3*4 + 3] = 0xFF;
                        }
                        else
                        {
                            for(u32 i = 0; i < 3; ++i)
                            {
                                colors8[2*4 + i] = (colors8[0*4 + i] + colors8[1*4 + i]) >> 1;
                            }
                            colors8[2*4 + 3] = 0xFF;

                            colors8[3*4 + 0] = 0;
                            colors8[3*4 + 1] = 0;
                            colors8[3*4 + 2] = 0;
                            colors8[3*4 + 3] = 0;
                        }

                        for(u32 yi = 0; yi < 4; ++yi)
                        {
                            u8 * optr = dst_image_buf;
                            optr += xo * 4 * 4;  // block offset in X
                            optr += yo * 4 * 4 * nx; // block offset in Y
                            optr += yi * 4 * nx; // pixel offset in Y
                            for(u32 xi = 0; xi < 4; ++xi)
                            {
                                *((u32*)optr) = colors[cidx & 0x3];
                                cidx = cidx >> 2;

                                *(optr + 3) = alpha[aidx & 0x7];
                                aidx = aidx >> 3;

                                optr += 4;
                            }
                        }
                    }
                }
                return 0;
            }
            break;
        case 80:
            {
                if(nx < 4) nx = 4;
                if(ny < 4) ny = 4;
                u32 bnx = nx >> 2;
                u32 bny = ny >> 2;
                u8 const * iptr = src_buffer_buf;
                for(u32 yo = 0; yo < bny; ++yo)
                {
                    for(u32 xo = 0;  xo < bnx; ++xo)
                    {
                        u8 const red_0 = *((u8 const*)(iptr + 0));
                        u8 const red_1 = *((u8 const*)(iptr + 1));
                        u64 const r0 = *((u16 const*)(iptr + 2));
                        u64 const r1 = *((u16 const*)(iptr + 4));
                        u64 const r2 = *((u16 const*)(iptr + 6));
                        u64 ridx = r2 << 32 | r1 << 16 | r0;
                        iptr += 8;

                        u8 red[8];

                        red[0] = red_0;
                        red[1] = red_1;
                        if(red_0 > red_1)
                        {
                            // 6 interpolated red values.
                            red[2] = (6 * (u16)red_0 + 1 * (u16)red_1) / 7;  // bit code 010
                            red[3] = (5 * (u16)red_0 + 2 * (u16)red_1) / 7;  // bit code 011
                            red[4] = (4 * (u16)red_0 + 3 * (u16)red_1) / 7;  // bit code 100
                            red[5] = (3 * (u16)red_0 + 4 * (u16)red_1) / 7;  // bit code 101
                            red[6] = (2 * (u16)red_0 + 5 * (u16)red_1) / 7;  // bit code 110
                            red[7] = (1 * (u16)red_0 + 6 * (u16)red_1) / 7;  // bit code 111
                        }
                        else
                        {
                            // 4 interpolated red values.
                            red[2] = (4 * (u16)red_0 + 1 * (u16)red_1) / 5;  // bit code 010
                            red[3] = (3 * (u16)red_0 + 2 * (u16)red_1) / 5;  // bit code 011
                            red[4] = (2 * (u16)red_0 + 3 * (u16)red_1) / 5;  // bit code 100
                            red[5] = (1 * (u16)red_0 + 4 * (u16)red_1) / 5;  // bit code 101
                            red[6] = 0;  // bit code 110
                            red[7] = 255;  // bit code 111
                        }

                        for(u32 yi = 0; yi < 4; ++yi)
                        {
                            u8 * optr = dst_image_buf;
                            optr += xo * 4 * 4;  // block offset in X
                            optr += yo * 4 * 4 * nx; // block offset in Y
                            optr += yi * 4 * nx; // pixel offset in Y
                            for(u32 xi = 0; xi < 4; ++xi)
                            {
                                *(optr + 0) = red[ridx & 0x3];
                                *(optr + 1) = 0;
                                *(optr + 2) = 0;
                                *(optr + 3) = 255;

                                ridx = ridx >> 3;
                                optr += 4;
                            }
                        }
                    }
                }
                return 0;
            }
            break;
        case 83:
            {
                if(nx < 4) nx = 4;
                if(ny < 4) ny = 4;
                u32 bnx = nx >> 2;
                u32 bny = ny >> 2;
                u8 const * iptr = src_buffer_buf;
                for(u32 yo = 0; yo < bny; ++yo)
                {
                    for(u32 xo = 0;  xo < bnx; ++xo)
                    {
                        u8 const red_0 = *((u8 const*)(iptr + 0));
                        u8 const red_1 = *((u8 const*)(iptr + 1));
                        u64 const r0 = *((u16 const*)(iptr + 2));
                        u64 const r1 = *((u16 const*)(iptr + 4));
                        u64 const r2 = *((u16 const*)(iptr + 6));
                        u64 ridx = r2 << 32 | r1 << 16 | r0;
                        iptr += 8;

                        u8 red[8];

                        red[0] = red_0;
                        red[1] = red_1;
                        if(red_0 > red_1)
                        {
                            // 6 interpolated red values.
                            red[2] = (6 * (u16)red_0 + 1 * (u16)red_1) / 7;  // bit code 010
                            red[3] = (5 * (u16)red_0 + 2 * (u16)red_1) / 7;  // bit code 011
                            red[4] = (4 * (u16)red_0 + 3 * (u16)red_1) / 7;  // bit code 100
                            red[5] = (3 * (u16)red_0 + 4 * (u16)red_1) / 7;  // bit code 101
                            red[6] = (2 * (u16)red_0 + 5 * (u16)red_1) / 7;  // bit code 110
                            red[7] = (1 * (u16)red_0 + 6 * (u16)red_1) / 7;  // bit code 111
                        }
                        else
                        {
                            // 4 interpolated red values.
                            red[2] = (4 * (u16)red_0 + 1 * (u16)red_1) / 5;  // bit code 010
                            red[3] = (3 * (u16)red_0 + 2 * (u16)red_1) / 5;  // bit code 011
                            red[4] = (2 * (u16)red_0 + 3 * (u16)red_1) / 5;  // bit code 100
                            red[5] = (1 * (u16)red_0 + 4 * (u16)red_1) / 5;  // bit code 101
                            red[6] = 0;  // bit code 110
                            red[7] = 255;  // bit code 111
                        }

                        u8 const green_0 = *((u8 const*)(iptr + 0));
                        u8 const green_1 = *((u8 const*)(iptr + 1));
                        u64 const g0 = *((u16 const*)(iptr + 2));
                        u64 const g1 = *((u16 const*)(iptr + 4));
                        u64 const g2 = *((u16 const*)(iptr + 6));
                        u64 gidx = g2 << 32 | g1 << 16 | g0;
                        iptr += 8;

                        u8 green[8];

                        green[0] = green_0;
                        green[1] = green_1;
                        if(green_0 > green_1)
                        {
                            // 6 interpolated green values.
                            green[2] = (6 * (u16)green_0 + 1 * (u16)green_1) / 7;  // bit code 010
                            green[3] = (5 * (u16)green_0 + 2 * (u16)green_1) / 7;  // bit code 011
                            green[4] = (4 * (u16)green_0 + 3 * (u16)green_1) / 7;  // bit code 100
                            green[5] = (3 * (u16)green_0 + 4 * (u16)green_1) / 7;  // bit code 101
                            green[6] = (2 * (u16)green_0 + 5 * (u16)green_1) / 7;  // bit code 110
                            green[7] = (1 * (u16)green_0 + 6 * (u16)green_1) / 7;  // bit code 111
                        }
                        else
                        {
                            // 4 interpolated green values.
                            green[2] = (4 * (u16)green_0 + 1 * (u16)green_1) / 5;  // bit code 010
                            green[3] = (3 * (u16)green_0 + 2 * (u16)green_1) / 5;  // bit code 011
                            green[4] = (2 * (u16)green_0 + 3 * (u16)green_1) / 5;  // bit code 100
                            green[5] = (1 * (u16)green_0 + 4 * (u16)green_1) / 5;  // bit code 101
                            green[6] = 0;  // bit code 110
                            green[7] = 255;  // bit code 111
                        }

                        for(u32 yi = 0; yi < 4; ++yi)
                        {
                            u8 * optr = dst_image_buf;
                            optr += xo * 4 * 4;  // block offset in X
                            optr += yo * 4 * 4 * nx; // block offset in Y
                            optr += yi * 4 * nx; // pixel offset in Y
                            for(u32 xi = 0; xi < 4; ++xi)
                            {
                                *(optr + 0) = red[ridx & 0x3];
                                *(optr + 1) = green[gidx & 0x3];
                                *(optr + 2) = 0;
                                *(optr + 3) = 255;

                                ridx = ridx >> 3;
                                gidx = gidx >> 3;
                                optr += 4;
                            }
                        }
                    }
                }
                return 0;
            }
            break;

        default:
            return -1; // FORMAT NOT HANDLED
    }
    return -2; //OTHER ERROR
}

#ifdef __cplusplus
}
#endif
