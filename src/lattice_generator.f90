program LatticeGenerator

use iso_fortran_env, only: dp => real64
implicit none

! --- constants --- !
real(dp), parameter :: r2 = sqrt(2.0_dp)
real(dp), parameter :: r3 = sqrt(3.0_dp)
real(dp), parameter :: r6 = sqrt(6.0_dp)

real(dp), parameter :: a_val = 4.05_dp ! lattice constant
real(dp), parameter :: b_val = a_val / r2 ! burgers vector value
! --- !

character(:), allocatable :: filename, x_str, y_str, z_str
integer :: fileunit

real(dp) :: t_start, t_end ! timing variables

real(dp) :: cell_atoms(6, 3) ! periodic atom coordinates in a unit cell
real(dp) :: cell_dim(3)      ! unit cell dimensions (oriented unit cell lengths in each dimension)
real(dp) :: box_dim(3, 2)    ! box dimensions (min/max in each dimension)

real(dp), allocatable :: atoms(:, :, :) ! all atom positions

integer :: cell_number(3) ! number of unit cells along each dimension

logical, allocatable :: active_cells(:) ! (PAD) cells to 'render' 

integer :: cells_total ! total number of cells

integer :: i, j, k, l
integer :: cell_counter
integer :: atom_id

integer :: structure_choice

write(*,*) 'This script will generate FCC crystal lattice with orientation:'
write(*,*) ' - X: [110]'
write(*,*) ' - Y: [111]'
write(*,*) ' - Z: [112]'
write(*,*) 'Considering a=4.05 (Al).'

! atom positions in the reference unit cell
cell_atoms(1,1) = a_val/2.0_dp/r2
cell_atoms(1,2) = 0.0_dp
cell_atoms(1,3) = a_val*3.0_dp/2.0_dp/r6

cell_atoms(2,1) = a_val/2.0_dp/r2
cell_atoms(2,2) = a_val/r3
cell_atoms(2,3) = a_val*5.0_dp*r6/12.0_dp

cell_atoms(3,1) = 0.0_dp
cell_atoms(3,2) = 0.0_dp
cell_atoms(3,3) = 0.0_dp

cell_atoms(4,1) = 0.0_dp
cell_atoms(4,2) = a_val/r3
cell_atoms(4,3) = a_val/r6

cell_atoms(5,1) = a_val/2.0_dp/r2
cell_atoms(5,2) = a_val*2.0_dp/r3
cell_atoms(5,3) = a_val/2.0_dp/r6

cell_atoms(6,1) = 0.0_dp
cell_atoms(6,2) = a_val*2.0_dp/r3
cell_atoms(6,3) = a_val*2.0_dp/r6

! size of the unit cell
cell_dim(1) = a_val/r2
cell_dim(2) = a_val*r3
cell_dim(3) = a_val*3.0_dp/r6

write(*,*) 'number of unit cells along X, Y, Z:'
write(*,*) '(!) X - odd, Y - even, Z - any'
read(*,*) cell_number(1), cell_number(2), cell_number(3)

cells_total = cell_number(1) * cell_number(2) * cell_number(3)

! (1) -> "cell id" \in [1, cells_total]
! (2) -> "atom id in a unit cell" \in [1, 6]
! (3) -> "global atom coordinate" (x, y, z)
allocate(atoms(cells_total, 6, 3))

! generate all atomic positions
cell_counter = 0
do i=1, cell_number(1)         ! x
    do j=1, cell_number(2)     ! y
        do k=1, cell_number(3) ! z
            cell_counter = cell_counter + 1
            do l=1, 6
                atoms(cell_counter, l, 1) = cell_atoms(l, 1) + (i-1) * cell_dim(1)
                atoms(cell_counter, l, 2) = cell_atoms(l, 2) + (j-1) * cell_dim(2)
                atoms(cell_counter, l, 3) = cell_atoms(l, 3) + (k-1) * cell_dim(3)
            end do
        end do
    end do
end do

write(*,*) 'What kind of crystal structure to generate?'
write(*,*) '1. Perfect FCC'
write(*,*) '2. PAD (Periodic Array of Dislocations)'
read(*,*)  structure_choice

allocate(character(len=8) :: x_str)
allocate(character(len=8) :: y_str)
allocate(character(len=8) :: z_str)
allocate(character(len=len(x_str)+len(y_str)+len(z_str)+16) :: filename)

write(x_str,'(I0)') cell_number(1)
write(y_str,'(I0)') cell_number(2)
write(z_str,'(I0)') cell_number(3)

call cpu_time(t_start)

select case (structure_choice)
    case(1) ! "Perfect FCC"
        filename = 'atoms.' // trim(x_str) // 'x' // trim(y_str) // 'x' // trim(z_str) // '.perfect'

        write(*,'(A, A, A)') 'Writing "Perfect FCC" atom data to "', trim(filename), '"...'

        box_dim = 0.0_dp
        box_dim(1, 2) = cell_number(1) * cell_dim(1)
        box_dim(2, 2) = cell_number(2) * cell_dim(2)
        box_dim(3, 2) = cell_number(3) * cell_dim(3)

        ! write actual data to the file (LAMMPS formatting)
        open(newunit=fileunit, file=filename, status='replace')
        write(fileunit,*) 'Position data for Al File'
        write(fileunit,*)
        write(fileunit,*) cells_total * 6, 'atoms'
        write(fileunit,*) '2 atom types'
        write(fileunit,*) box_dim(1, 1:2), 'xlo xhi'
        write(fileunit,*) box_dim(2, 1:2), 'ylo yhi'
        write(fileunit,*) box_dim(3, 1:2), 'zlo zhi'
        write(fileunit,*)
        write(fileunit,*) 'Atoms'
        write(fileunit,*)

        atom_id = 1
        cell_counter = 0
        do i=1, cell_number(1)         ! x
            do j=1, cell_number(2)     ! y
                do k=1, cell_number(3) ! z
                    cell_counter = cell_counter + 1
                    do l=1, 6
                        write(fileunit,10) atom_id, 1, atoms(cell_counter, l, 1:3)
                        atom_id = atom_id + 1
                    end do
                end do
            end do
        end do

    case(2) ! "PAD"
        filename = 'atoms.' // trim(x_str) // 'x' // trim(y_str) // 'x' // trim(z_str) // '.pad'

        write(*,'(A, A, A)') 'Writing "PAD" atom data to "', trim(filename), '"...'

        allocate(active_cells(cells_total))
        active_cells = .true.

        ! removing half-plane of atoms from the right edge
        ! (starting counting from the last vertical Oyz plane)
        cell_counter = cell_number(3) * cell_number(2) * (cell_number(1) - 1)
        do j=1, cell_number(2)     ! y
            do k=1, cell_number(3) ! z
                cell_counter = cell_counter + 1
                if (j <= cell_number(2) / 2) then
                    active_cells(cell_counter) = .false.
                end if
            end do
        end do

        cell_counter = 0
        do i=1, cell_number(1)         ! x
            do j=1, cell_number(2)     ! y
                do k=1, cell_number(3) ! z
                    cell_counter = cell_counter + 1
                    do l=1, 6
                        ! about these formulas (e.g. upper one, lower is just with "-b/2"):
                        ! 1. x' = x + b/2 - basic shifting by b/2.
                        ! 2. x' = x + (b/2)(x/L), where L = (Nx-1)dx - linear interpolation, spacing atoms evenly in each half.
                        ! about linear interpolation:
                        ! x' = x + s(x), where s(x) "shift" = (b/2)(x/L).
                        ! full length: Lx = Nx*dx. Our L is one dx shorter, because we deleted one half-plane.
                        if (j <= cell_number(2) / 2) then
                            atoms(cell_counter, l, 1) = atoms(cell_counter, l, 1) * (1.0_dp + 0.5_dp * b_val / (cell_number(1)-1) / cell_dim(1))
                        else
                            atoms(cell_counter, l, 1) = atoms(cell_counter, l, 1) * (1.0_dp - 0.5_dp * b_val / (cell_number(1)-1) / cell_dim(1))
                        end if
                    end do
                end do
            end do
        end do

        box_dim = 0.0_dp
        box_dim(1, 2) = (cell_number(1)-1) * cell_dim(1) + b_val * 0.5_dp
        box_dim(2, 2) = cell_number(2) * cell_dim(2)
        box_dim(3, 2) = cell_number(3) * cell_dim(3)

        ! write actual data to the file (LAMMPS formatting)
        open(newunit=fileunit, file=filename, status='replace')
        write(fileunit,*) 'Position data for Al File'
        write(fileunit,*)
        write(fileunit,*) (cells_total - cell_number(3) * cell_number(2) / 2) * 6, 'atoms'
        write(fileunit,*) '2 atom types'
        write(fileunit,*) box_dim(1, 1:2), ' xlo xhi'
        write(fileunit,*) box_dim(2, 1:2), ' ylo yhi'
        write(fileunit,*) box_dim(3, 1:2), ' zlo zhi'
        write(fileunit,*)
        write(fileunit,*) 'Atoms'
        write(fileunit,*)

        atom_id = 1
        cell_counter = 0
        do i=1, cell_number(1)         ! x
            do j=1, cell_number(2)     ! y
                do k=1, cell_number(3) ! z
                    cell_counter = cell_counter + 1
                    do l=1, 6
                        if (active_cells(cell_counter)) then
                            write(fileunit,10) atom_id, 1, atoms(cell_counter, l, 1:3)
                            atom_id = atom_id + 1
                        endif
                    end do
                end do
            end do
        end do
end select

close(fileunit)

call cpu_time(t_end)

write(*,'(A, F8.4, A)') 'Total time elapsed:', t_end - t_start, ' sec'

10 format(i8, i8, 3(1x, e12.5))

end program
